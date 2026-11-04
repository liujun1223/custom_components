"""The Egreat Player integration."""

import json
import logging
import re
import socket
import struct
import subprocess

import serial

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BAUDRATE,
    CONF_HOST,
    CONF_PORT,
    DOMAIN,
    IP_CONTROL_PORT,
    RESPONSE_HEADER,
)

_LOGGER = logging.getLogger(__name__)

# 声明集成支持的平台：MEDIA_PLAYER + SELECT
_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SELECT]

# 配置入口类型别名
type EgreatPlayerConfigEntry = ConfigEntry[EgreatPlayer]


class EgreatPlayer:
    """Egreat Player API，封装串口与 TCP 两种控制通路。."""

    def __init__(
        self, port: str, baudrate: int, host: str | None = None
    ) -> None:
        """初始化播放器实例；host 可选，仅用于 IP 控制与设备信息查询。."""
        self._port = port
        self._baudrate = baudrate
        self._host = host
        self.mac_address: str | None = None
        self.model: str | None = None
        self.sw_version: str | None = None
        self._serial_connection: serial.Serial | None = None
        self.available = False

    def connect(self) -> bool:
        """建立或探活串口连接。."""
        if self._serial_connection is not None and self._serial_connection.is_open:
            try:
                # 访问 in_waiting 触发实际的端口探活；若串口已死会抛异常
                _ = self._serial_connection.in_waiting
            except (serial.SerialException, OSError) as err:
                _LOGGER.debug("Serial connection dead: %s", err)
                try:
                    self._serial_connection.close()
                except OSError as close_err:
                    _LOGGER.debug("Failed to close dead connection: %s", close_err)
                self._serial_connection = None
                self.available = False
            else:
                return True

        try:
            self._serial_connection = serial.Serial(
                self._port, self._baudrate, timeout=1
            )
        except serial.SerialException as e:
            self._serial_connection = None
            self.available = False
            _LOGGER.error("Failed to connect to %s: %s", self._port, e)
            return False
        else:
            self.available = True
            _LOGGER.info("Connected to egreat player on %s", self._port)
            return True

    def send_command(self, command: bytes) -> bool:
        """通过串口发送控制命令并校验响应帧头。."""
        if not self.connect() or self._serial_connection is None:
            return False

        try:
            self._serial_connection.reset_input_buffer()
            self._serial_connection.write(command)
            self._serial_connection.flush()
            _LOGGER.debug("Send command: %s", command.hex())

            response = self._serial_connection.read_until(b"\xD0", size=20)
            _LOGGER.debug("Response: %s", response.hex())

            if not response:
                _LOGGER.debug("No response received")
                return False
            if response[0] != RESPONSE_HEADER:
                _LOGGER.debug("Invalid response header: %s", response.hex())
                return False
        except (serial.SerialException, OSError) as e:
            self.available = False
            self._serial_connection = None
            _LOGGER.error("Error send command: %s", e)
            return False
        else:
            return True

    def send_ip_command(self, command: str) -> bool:
        """通过 TCP 33080 发送 IP 控制命令."""
        if self._host is None:
            return False
        try:
            with socket.create_connection(
                (self._host, IP_CONTROL_PORT), timeout=3
            ) as sock:
                sock.sendall(command.encode("utf-8"))
            _LOGGER.info("IP command sent: %s", command)
        except OSError as e:
            _LOGGER.error("Failed to send IP command %s: %s", command, e)
            return False
        else:
            return True

    @property
    def host(self) -> str | None:
        """返回当前的 IP 地址配置。."""
        return self._host

    def close(self) -> None:
        """关闭串口连接并释放资源。."""
        if self._serial_connection is not None and self._serial_connection.is_open:
            self._serial_connection.close()
            _LOGGER.info("Closed connection to %s", self._port)

    def get_device_info(self, ip: str) -> dict | None:
        """通过 TCP 26047 端口查询设备信息（型号、版本、MAC 等）。."""
        try:
            with socket.create_connection((ip, 26047), timeout=3) as sock:
                body = json.dumps({"cmd": "getDeviceInfo"}).encode("utf-8")
                header = struct.pack("!i", len(body))
                sock.sendall(header + body)
                response = b""
                while True:
                    chunk = sock.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                    if b"}" in response:
                        break
        except OSError:
            _LOGGER.exception("Failed to connect to %s for device info", ip)
            return None
        except (json.JSONDecodeError, struct.error):
            _LOGGER.exception("Malformed response from %s", ip)
            return None

        if len(response) < 4:
            _LOGGER.error("Response data too short, no device info")
            return None
        struct.unpack("!i", response[:4])
        playroad = response[4:]
        data = json.loads(playroad.decode("utf-8"))
        if data.get("status") == "success":
            _LOGGER.debug("Device info: %s", data)
            return data
        return None

    def get_mac_from_ip(self, ip: str) -> str | None:
        """通过 ARP 获取 MAC 地址（当 TCP 查询没有返回 MAC 时的备用方案）。."""
        try:
            subprocess.run(
                ["ping", "-c", "1", ip],
                check=False,
                capture_output=True,
                timeout=1,
            )
            result = subprocess.run(
                ["arp", "-n", ip],
                check=False,
                capture_output=True,
                text=True,
                timeout=1,
            )
            match = re.search(
                r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}",
                result.stdout,
            )
            if match:
                return match.group(0)
        except (OSError, subprocess.TimeoutExpired):
            _LOGGER.exception("Failed to get MAC for IP %s", ip)

        return None


# ---------------------------------------------------------------------------
# 配置入口生命周期
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant, entry: EgreatPlayerConfigEntry
) -> bool:
    """Set up Egreat Player from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    player = EgreatPlayer(
        entry.data[CONF_PORT],
        entry.data[CONF_BAUDRATE],
        host=entry.data.get(CONF_HOST),
    )

    # 通过 TCP 查询设备信息（MAC、型号、版本），失败降级用 ARP
    if player.host:
        device_info = await hass.async_add_executor_job(
            player.get_device_info, player.host
        )
        if device_info:
            player.mac_address = device_info.get("mac")
            player.model = device_info.get("model")
            player.sw_version = device_info.get("version")
            _LOGGER.info(
                "Device info: model=%s, version=%s, mac=%s",
                player.model,
                player.sw_version,
                player.mac_address,
            )
        else:
            _LOGGER.debug("TCP query failed, falling back to ARP")
            player.mac_address = await hass.async_add_executor_job(
                player.get_mac_from_ip, player.host
            )

    # 测试串口连接
    connected = await hass.async_add_executor_job(player.connect)
    if not connected:
        return False

    entry.runtime_data = player
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EgreatPlayerConfigEntry
) -> bool:
    """Unload a config entry."""
    player = entry.runtime_data
    await hass.async_add_executor_job(player.close)
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
