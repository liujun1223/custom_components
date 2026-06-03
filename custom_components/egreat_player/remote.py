"""remote platform for Egreat Player"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from homeassistant.components.remote import RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EgreatPlayer, EgreatPlayerConfigEntry
from .const import *

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: EgreatPlayerConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """加载remote实体"""

    player:EgreatPlayer = entry.runtime_data

    async_add_entities([EgreatRemote(entry.entry_id, player)])

# 协议命令映射
COMMAND_MAP: dict[str, bytes] = {
    # 导航
    "up": CMD_UP,
    "down": CMD_DOWN,
    "left": CMD_LEFT,
    "right": CMD_RIGHT,
    "ok": CMD_OK,
    "enter": CMD_OK,

    # 系统
    "home": CMD_HOME,
    "menu": CMD_MENU,
    "back": CMD_BACK,
    "setup": CMD_SETUP,

    # 播放控制
    "play": CMD_PLAY,
    "pause": CMD_PAUSE,
    "stop": CMD_STOP,
    "play_pause": CMD_PLAY_PAUSE,

    # 快进快退
    "ff": CMD_FF,
    "fb": CMD_FB,

    # 上一首下一首
    "previous": CMD_PREVIOUS,
    "prev": CMD_PREVIOUS,
    "next": CMD_NEXT,

    # 音量
    "volume_up": CMD_VOLUME_UP,
    "volume_down": CMD_VOLUME_DOWN,
    "mute": CMD_MUTE,

    # 字幕音轨
    "subtitle": CMD_SUBTITLE,
    "audio": CMD_AUDIO,

    # 信息
    "info": CMD_INFO,

    # 蓝光菜单
    "top_menu": CMD_TOP_MENU,
    "pop_menu": CMD_POP_MENU,

    # 文件分类
    "file": CMD_FILE,
    "video": CMD_VIDEO,
    "music": CMD_MUSIC,
    "photo": CMD_PHOTO,

    # 播放功能
    "repeat": CMD_REPEAT,
    "goto": CMD_GOTO,
    "bookmark": CMD_BOOKMARK,
    "slow": CMD_SLOW,
    "karaoke": CMD_KARAOKE,

    # 显示
    "ratio": CMD_RATIO,
    "scale": CMD_SCALE,
    "resolution": CMD_RESOLUTION,

    # 彩色键
    "red": CMD_RED,
    "green": CMD_GREEN,
    "yellow": CMD_YELLOW,
    "blue": CMD_BLUE,

    # 电源
    "power_on": CMD_POWER_ON,
    "power_off": CMD_POWER_OFF,

    # 数字键
    "0": CMD_0,
    "1": CMD_1,
    "2": CMD_2,
    "3": CMD_3,
    "4": CMD_4,
    "5": CMD_5,
    "6": CMD_6,
    "7": CMD_7,
    "8": CMD_8,
    "9": CMD_9
}

class EgreatRemote(RemoteEntity):
    """Egreat 遥控器实体"""

    _attr_should_poll = False

    def __init__(self, entry_id: str, device: EgreatPlayer) -> None:
        """初始化遥控器模块"""

        self._device = device
        self._attr_name = "Egreat Remote"
        self._attr_unique_id = (f"{entry_id}_remote")

    def available(self) -> bool:
        """设备是否在线"""

        return self._device.available

    async def _send_command(self, command: bytes) -> bool:
        """发送串口命令"""

        return await self.hass.async_add_executor_job(
            self._device.send_command,
            command
        )

    async def async_send_command(self, command: Iterable[str], **kwargs) -> None:
        """发送遥控命令"""

        for cmd in command:
            serial_cmd = COMMAND_MAP.get(cmd.lower())
            if serial_cmd is None:
                _LOGGER.warning("Unknown command: %s", cmd)
                continue

            success = await self._send_command(serial_cmd)
            if not success:
                _LOGGER.warning("Failed to send command: %s", cmd)
            else:
                _LOGGER.debug("Command sent: %s", cmd)

    async def async_turn_on(self, **kwargs) -> None:
        await self._send_command(CMD_POWER_ON)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send_command(CMD_POWER_OFF)