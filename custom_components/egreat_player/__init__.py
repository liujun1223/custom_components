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

from .const import CONF_BAUDRATE, CONF_HOST, CONF_PORT, DOMAIN, RESPONSE_HEADER

_LOGGER = logging.getLogger(__name__)

# For your initial PR, limit it to 1 platform.
# 声明集成支持的平台：MEDIA_PLAYER
_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.REMOTE, Platform.SELECT]

# 配置入口类型别名
type EgreatPlayerConfigEntry = ConfigEntry[EgreatPlayer]


class EgreatPlayer:
    """Egreat Player Api!"""
    # 初始化串口连接参数
    def __init__(self, port: str, baudrate: int, host: str | None = None) -> None:
        self._port = port
        self._baudrate = baudrate
        self._host = host
        # 初始化MAC地址
        self.mac_address: str | None = None
        # 设备型号
        self.model: str | None = None
        # 软件版本
        self.sw_version: str | None = None
        # 串口连接对象
        self._serial_connection = None
        # 设备在线状态
        self.available = False

    # 连接串口设备
    def connect(self) -> bool:
        # 已连接时探活
        if self._serial_connection and self._serial_connection.is_open:
            try:
                self._serial_connection.in_waiting
                return True  # 串口健康，直接返回
            except Exception as err:
                _LOGGER.debug("Serial connection dead: %s", err)
                # 串口已死，强制关闭
                try:
                    self._serial_connection.close()
                except Exception as close_err:
                    _LOGGER.debug("Failed to close dead connection: %s", close_err)
                self._serial_connection = None
                self.available = False

        # 重新建立连接
        try:
            self._serial_connection = serial.Serial(
                self._port, self._baudrate, timeout=1
            )
            self.available = True
            _LOGGER.info("Connected to egreat player on %s", self._port)
            return True
        except serial.SerialException as e:
            self._serial_connection = None  # 确保失败时置None
            self.available = False
            _LOGGER.error("Failed to connect to %s: %s", self._port, e)
            return False

    # 发送串口控制命令
    def send_command(self, command: bytes) -> bool:
        # 自动重连
        if not self.connect():
            return False

        # 防御检查，connect()成功但_serial_connection为None时直接返回
        if self._serial_connection is None:
            _LOGGER.error("Serial connection is None after connect() succeeded")
            return False

        try:
            # 清空历史缓存
            self._serial_connection.reset_input_buffer()

            # 发送命令
            self._serial_connection.write(command)
            self._serial_connection.flush()
            _LOGGER.debug("Send command: %s", command.hex())

            # 读取设备反馈码，直到D0,设置size上限20
            response = self._serial_connection.read_until(b"\xD0", size = 20)
            _LOGGER.debug("Response: %s", response.hex())

            # 没收到反馈
            if not response:
                _LOGGER.debug("No response received")
                return False

            # 验证协议头
            if response[0] != RESPONSE_HEADER:
                _LOGGER.debug("Invalid response header: %s", response.hex())
                return False

            return True
        except Exception as e:
            self.available = False
            self._serial_connection = None
            _LOGGER.error("Error send command: %s", e)
            return False

    # 关闭串口连接
    def close(self) -> None:
        if self._serial_connection and self._serial_connection.is_open:
            self._serial_connection.close()
            _LOGGER.info("Closed connection to %s", self._port)

    # 通过TCP 26047端口查询设备信息(型号，版本，MAC等)
    def get_device_info(self, ip: str) -> dict | None:
        try:
            with socket.create_connection((ip, 26047), timeout = 3) as sock:
                body = json.dumps({"cmd": "getDeviceInfo"}).encode("utf-8")
                header = struct.pack("!i", len(body))
                sock.sendall(header + body)
                response = b""
                while True:
                    chunk = sock.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                    # 收到完整的json后退出
                    if b"}" in response:
                        break
            if len(response) < 4:
                _LOGGER.error("Response data process")
            length = struct.unpack("!i", response[:4])[0]
            playroad = response[4:]
            _LOGGER.warning("Length = %d", length)
            _LOGGER.warning("Playroad = %r", playroad)
            data = json.loads(playroad.decode("utf-8"))
            if data.get("status") == "success":
                _LOGGER.debug("Device info: %s", data)
                return data
        except Exception:
            _LOGGER.exception("Failed to get device info from %s", ip)
            return None

    # 通过arp获取MAC地址(备用，当TCP查询没有返回MAC时使用)
    def get_mac_from_ip(self, ip: str) -> str | None:
        try:
            subprocess.run(["ping", "-c", "1", ip], capture_output=True, timeout=1)
            result = subprocess.run(
                ["arp", "-n", ip], capture_output=True, text=True, timeout=1
            )
            match = re.search(
                r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}",
                result.stdout
            )
            if match:
                return match.group(0)
        except Exception:
            _LOGGER.exception("Failed to get MAC for IP %s", ip)

        return None


# 配置入口设置函数的功能
async def async_setup_entry(
    hass: HomeAssistant, entry: EgreatPlayerConfigEntry
) -> bool:
    """Set up Egreat Player from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # 创建播放器实例
    player = EgreatPlayer(entry.data[CONF_PORT], entry.data[CONF_BAUDRATE], host = entry.data.get(CONF_HOST))
    # 通过TCP查询设备信息(MAC，型号，版本)
    if player._host:
        device_info = await hass.async_add_executor_job(
            player.get_device_info,
            player._host,
        )
        if device_info:
            player.mac_address = device_info.get("mac")
            player.model = device_info.get("model")
            player.sw_version = device_info.get("version")
            _LOGGER.info("Device info: model = %s, version = %s, mac = %s", player.model, player.sw_version, player.mac_address)
        else:
            # TCP查询失败，降级用ARP获取MAC
            _LOGGER.debug("TCP query failed, faling back to ARP")
            player.mac_address = await hass.async_add_executor_job(
                player.get_mac_from_ip,
                player._host,
            )

    # 测试连接
    connected = await hass.async_add_executor_job(player.connect)
    if not connected:
        return False

    # 存储API对象供平台使用
    entry.runtime_data = player

    # 转发到各平台
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True

# 配置卸载函数的功能
async def async_unload_entry(hass: HomeAssistant, entry: EgreatPlayerConfigEntry) -> bool:
    """Unload a config entry."""
    # 关闭串口连接
    player = entry.runtime_data
    await hass.async_add_executor_job(player.close)

    #卸载平台
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

    return unload_ok