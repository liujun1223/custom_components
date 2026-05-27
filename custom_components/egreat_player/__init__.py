"""The Egreat Player integration."""

import logging
import serial

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_PORT, CONF_BAUDRATE

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
# 声明集成支持的平台：MEDIA_PLAYER
_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]

# TODO Create ConfigEntry type alias with API object
# TODO Rename type alias and update all entry annotations
# 创建类型别名EgreatPlayerConfigEntry，指定ConfigEntry的泛型参数为EgreatPlayer
type EgreatPlayerConfigEntry = ConfigEntry[EgreatPlayer]  # noqa: F821


class EgreatPlayer:
    """Egreat Player Api"""
    # 初始化串口连接
    def __init__(self, port:str, baudrate:int) -> None:
        self._port = port
        self._baudrate = baudrate
        self._serial_connection = None

    # 连接串口
    def connect(self) -> bool:
        try:
            self._serial_connection = serial.Serial(self._port, self._baudrate, timeout = 1)
            _LOGGER.info("Connnected to egreat player on %s", self._port)
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect to %s: %s", self._port, e)
            return False

    # 发送串口命令
    def send_command(self, command:bytes) -> bool:
        if not self._serial_connection or not self._serial_connection.is_open:
            if not self.connect():
                return False

        try:
            self._serial_connection.write(command)
            _LOGGER.debug("Send command: %s", command.hex())
            return True
        except Exception as e:
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

    # 创建API实例
    port = entry.data[CONF_PORT]
    baudrate = entry.data[CONF_BAUDRATE]
    player = EgreatPlayer(port, baudrate)

    # 验证连接
    if not await hass.async_add_executor_job(player.connect):
        _LOGGER.error("Could not connect to Egreat player on %s", port)
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

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
