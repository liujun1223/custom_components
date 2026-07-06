"""Media Player platform for Egreat Player!"""

from datetime import timedelta
import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from . import EgreatPlayer, EgreatPlayerConfigEntry
from .const import (
    CMD_MUTE,
    CMD_NEXT,
    CMD_PAUSE,
    CMD_PLAY,
    CMD_POWER_OFF,
    CMD_POWER_ON,
    CMD_PREVIOUS,
    CMD_STOP,
    CMD_VOLUME_DOWN,
    CMD_VOLUME_UP,
    DOMAIN,
    IP_CMD_MAP,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EgreatPlayerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Egreat media player platform."""
    # 初始化播放器实体

    device = entry.runtime_data
    async_add_entities([EgreatMediaPlayer(entry.entry_id, device)])


class EgreatMediaPlayer(MediaPlayerEntity):
    """Representation of an Egreat Player!"""

    # 播放器实体

    # 不主动轮询
    _attr_should_poll = False

    def __init__(self, entry_id: str, device: EgreatPlayer) -> None:
        """Initialize the media player!"""
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
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
        )

        # 默认状态
        self._attr_state = MediaPlayerState.IDLE
        # 默认静音状态
        self._attr_is_volume_muted = False

    # 定时检查设备是否在线，并将状态变化通知HA更新前端显示
    async def async_added_to_hass(self) -> None:
        async_track_time_interval(
            self.hass, self._async_check_availability, timedelta(seconds=10)
        )

    async def _async_check_availability(self, _now=None) -> None:
        was_available = self._device.available
        is_available = await self.hass.async_add_executor_job(self._device.connect)
        if was_available != is_available:
            self.async_write_ha_state()

    # 设备信息
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            connections={(CONNECTION_NETWORK_MAC, self._device.mac_address)}
            if self._device.mac_address
            else set(),
            name=self._device.model,
            manufacturer="Egreat",
            model=self._device.model,
            sw_version=self._device.sw_version,
            configuration_url="http://www.egreatworld.com/",
        )

    # 返回设备是否在线
    @property
    def available(self) -> bool:
        return self._device.available

    async def _send_command(self, command: bytes, ip_key: str | None = None) -> bool:
        """发送控制命令,有IP时优先走IP控制,否则降级到串口
        ip_key: IP_CMD_MAP里的键名,None表示该命令没有对应的IP命令.
        """  # noqa: D205
        if ip_key and self._device._host:
            ip_cmd = IP_CMD_MAP(ip_key)
            if ip_cmd:
                success = await self.hass.async_add_executor_job(
                    self._device.send_ip_command, ip_cmd
                )
                if success:
                    return True
                _LOGGER.debug("IP command failed, falling back to serial: %s", ip_key)
        return await self.hass.async_add_executor_job(
            self._device.send_command, command
        )

    async def async_turn_on(self) -> None:
        """Turn on the player!"""
        if await self._send_command(CMD_POWER_ON, "power_on"):
            self._attr_state = MediaPlayerState.ON
            self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off the player!"""
        if await self._send_command(CMD_POWER_OFF, "power_off"):
            self._attr_state = MediaPlayerState.OFF
            self.async_write_ha_state()

    async def async_media_play(self) -> None:
        """Send play command!"""
        if await self._send_command(CMD_PLAY, "play"):
            self._attr_state = MediaPlayerState.PLAYING
            self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        """Send pause command!"""
        if await self._send_command(CMD_PAUSE, "pause"):
            self._attr_state = MediaPlayerState.PAUSED
            self.async_write_ha_state()

    async def async_media_stop(self) -> None:
        """Send stop command!"""
        if await self._send_command(CMD_STOP, "stop"):
            self._attr_state = MediaPlayerState.IDLE
            self.async_write_ha_state()

    async def async_media_previous_track(self) -> None:
        """Send previous track command!"""
        await self._send_command(CMD_PREVIOUS, "skip_rev")

    async def async_media_next_track(self) -> None:
        """Send next track command!"""
        await self._send_command(CMD_NEXT, "skip_fwd")

    async def async_volume_up(self) -> None:
        """Send volume up command!"""
        await self._send_command(CMD_VOLUME_UP, "volume_up")

    async def async_volume_down(self) -> None:
        """Send volume down command!"""
        await self._send_command(CMD_VOLUME_DOWN, "volume_down")

    async def async_mute_volume(self, mute: bool) -> None:
        """Send mute command!"""
        if await self._send_command(CMD_MUTE):
            self._attr_is_volume_muted = mute
            self.async_write_ha_state()
