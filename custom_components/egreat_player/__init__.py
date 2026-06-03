"""The Egreat Player integration."""

import logging
import serial

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_PORT, CONF_BAUDRATE, RESPONSE_HEADER

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
# 声明集成支持的平台：MEDIA_PLAYER
_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.REMOTE]

# TODO Create ConfigEntry type alias with API object
# TODO Rename type alias and update all entry annotations
# 配置入口类型别名
EgreatPlayerConfigEntry = ConfigEntry


class EgreatPlayer:
    """Egreat Player Api"""
    # 初始化串口连接参数
    def __init__(self, port:str, baudrate:int) -> None:
        self._port = port
        self._baudrate = baudrate
        # 串口连接对象
        self._serial_connection = None
        # 设备在线状态
        self.available = False

    # 连接串口设备
    def connect(self) -> bool:
        try:
            # 已连接时直接返回
            if self._serial_connection and self._serial_connection.is_open:
                return True

            # 创建串口连接
            self._serial_connection = serial.Serial(self._port, self._baudrate, timeout = 1)
            self.available = True
            _LOGGER.info("Connnected to egreat player on %s", self._port)
            return True
        except Exception as e:
            self.available = False
            _LOGGER.error("Failed to connect to %s: %s", self._port, e)
            return False

    # 发送串口控制命令
    def send_command(self, command:bytes) -> bool:
        # 自动重连
        if not self.connect():
            return False

        try:
            # 清空历史缓存
            self._serial_connection.reset_input_buffer()

            # 发送命令
            self._serial_connection.write(command)
            self._serial_connection.flush()
            _LOGGER.debug("Send command: %s", command.hex())

            # 读取设备反馈码，直到D0
            response = self._serial_connection.read_until(b"\xD0")
            _LOGGER.debug("Response: %s", response.hex())

            # 没收到反馈
            if not response:
                _LOGGER.warning("No response received")
                return False

            # 验证协议头
            if response[0] != RESPONSE_HEADER:
                _LOGGER.warning("Invalid response header: %s", response.hex())
                return False

            return True
        except Exception as e:
            self.available = False
            _LOGGER.error("Error send command: %s", e)
            return False

    #关闭串口连接
    def close(self) -> None:
        if self._serial_connection and self._serial_connection.is_open:
            self._serial_connection.close()
            _LOGGER.info("Closed connection to %s", self._port)


# TODO Update entry annotation
# 配置入口设置函数的功能
async def async_setup_entry(hass: HomeAssistant, entry: EgreatPlayerConfigEntry) -> bool:
    """Set up Egreat Player from a config entry."""

    # TODO 1. Create API instance
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for your platforms to access
    # entry.runtime_data = MyAPI(...)
    hass.data.setdefault(DOMAIN, {})

    # 创建播放器实例
    player = EgreatPlayer(entry.data[CONF_PORT], entry.data[CONF_BAUDRATE])

    # 测试连接
    connected = await hass.async_add_executor_job(player.connect)
    if not connected:
        return False

    # 存储API对象供平台使用
    entry.runtime_data = player

    # 转发到各平台
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


# TODO Update entry annotation
# 配置卸载函数的功能
async def async_unload_entry(hass: HomeAssistant, entry: EgreatPlayerConfigEntry) -> bool:
    """Unload a config entry."""
    # 关闭串口连接
    player = entry.runtime_data
    await hass.async_add_executor_job(player.close)

    #卸载平台
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

    return unload_ok
