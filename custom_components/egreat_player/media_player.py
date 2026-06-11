"""Media Player platform for Egreat Player"""

import logging

from homeassistant.components.media_player import (MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import (
    DOMAIN,
    CMD_POWER_ON,
    CMD_POWER_OFF,
    CMD_VOLUME_UP,
    CMD_VOLUME_DOWN,
    CMD_MUTE,
    CMD_PLAY,
    CMD_PAUSE,
    CMD_STOP,
    CMD_PREVIOUS,
    CMD_NEXT,
)
from . import EgreatPlayer, EgreatPlayerConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo, CONNECTION_NETWORK_MAC

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: EgreatPlayerConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Egreat media player platform."""
    # 初始化播放器实体

    device = entry.runtime_data
    async_add_entities([EgreatMediaPlayer(entry.entry_id, device)])

class EgreatMediaPlayer(MediaPlayerEntity):
    """Representation of an Egreat Player"""
    # 播放器实体

    # 不主动轮询
    _attr_should_poll = False

    def __init__(self, entry_id: str, device: EgreatPlayer) -> None:
        """Initialize the media player"""
        # 初始化播放器

        self._device = device
        self._entry_id = entry_id
        # 实体名称
        self._attr_name = "Media Player"
        self._attr_has_entity_name = True
        # 唯一ID
        self._attr_unique_id = f"{entry_id}_egreat_player"

        # 定义支持的功能
        self._attr_supported_features = (
            MediaPlayerEntityFeature.TURN_ON |
            MediaPlayerEntityFeature.TURN_OFF |
            MediaPlayerEntityFeature.PLAY |
            MediaPlayerEntityFeature.PAUSE |
            MediaPlayerEntityFeature.STOP |
            MediaPlayerEntityFeature.PREVIOUS_TRACK |
            MediaPlayerEntityFeature.NEXT_TRACK |
            MediaPlayerEntityFeature.VOLUME_STEP |
            MediaPlayerEntityFeature.VOLUME_MUTE
        )

        # 默认状态
        self._attr_state = MediaPlayerState.IDLE
        # 默认静音状态
        self._attr_is_volume_muted = False

    # 设备信息
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers = {(DOMAIN, self._entry_id)},
            connections = {(CONNECTION_NETWORK_MAC, self._device.mac_address)},
            name = "K5",
            manufacturer = "Egreat",
            model = "K5",
            sw_version = self._device.firmware_version,
            configuration_url="http://www.egreatworld.com/"
        )

    # 返回设备是否在线
    @property
    def available(self) -> bool:
        return self._device.available

    async def _send_command(self, command: bytes) -> bool:
        """
        统一发送串口命令。
        这里的作用：
        1. 把阻塞 IO 放进 executor
        2. 避免重复代码
        3. 后续方便扩展：
           - retry
           - timeout
           - command queue
           - logging
        """
        return await self.hass.async_add_executor_job(self._device.send_command, command)

    async def async_turn_on(self) -> None:
        """Turn on the player"""
        if await self._send_command(CMD_POWER_ON):
            self._attr_state = MediaPlayerState.ON
            self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off the player"""
        if await self._send_command(CMD_POWER_OFF):
            self._attr_state = MediaPlayerState.OFF
            self.async_write_ha_state()

    async def async_media_play(self) -> None:
        """send play command"""
        if await self._send_command(CMD_PLAY):
            self._attr_state = MediaPlayerState.PLAYING
            self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        """send pause command"""
        if await self._send_command(CMD_PAUSE):
            self._attr_state = MediaPlayerState.PAUSED
            self.async_write_ha_state()

    async def async_media_stop(self) -> None:
        """send stop command"""
        if await self._send_command(CMD_STOP):
            self._attr_state = MediaPlayerState.IDLE
            self.async_write_ha_state()

    async def async_media_previous_track(self) -> None:
        """send previous track command"""
        await self._send_command(CMD_PREVIOUS)

    async def async_media_next_track(self) -> None:
        """send next track command"""
        await self._send_command(CMD_NEXT)

    async def async_volume_up(self) -> None:
        """send volume up command"""
        await self._send_command(CMD_VOLUME_UP)

    async def async_volume_down(self) -> None:
        """send volume down command"""
        await self._send_command(CMD_VOLUME_DOWN)

    async def async_mute_volume(self, mute: bool) -> None:
        """send mute command"""
        if await self._send_command(CMD_MUTE):
            self._attr_is_volume_muted = mute
            self.async_write_ha_state()