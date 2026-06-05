"""select platform for Egreat Player"""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EgreatPlayer, EgreatPlayerConfigEntry
from .remote import COMMAND_MAP

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: EgreatPlayerConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """创建select实体"""

    player: EgreatPlayer = entry.runtime_data

    async_add_entities([EgreatCommandSelect(entry.entry_id, player)])

class EgreatCommandSelect(SelectEntity):
    """Egreat 命令选择器
    用于调试和快速发送遥控器命令。

    用户在 Home Assistant 前端选择某个命令后，
    会立即通过串口发送对应协议。
    """

    _attr_should_poll = False

    def __init__(self, entry_id: str, device: EgreatPlayer) -> None:
        """初始化实体"""

        self.device = device
        self._attr_name = "Egreat Command"
        self._attr_unique_id = (f"{self.entity_id}_command")
        self._attr_options = sorted(COMMAND_MAP.keys())
        self._attr_current_option = (self._attr_options[0])

    @property
    def available(self) -> bool:
        """设备是否在线"""

        return self._device.available

    async def async_select_option(self, option: str) -> None:
        """用户选择某个命令后执行
        例如：
        home
        menu
        选择后立即发送串口命令
        """

        # 获取对应协议
        command = COMMAND_MAP.get(option)
        if command is None:
            _LOGGER.warning("Unknown command: %s", option)
            return
        _LOGGER.debug("Send command: %s", option)

        # 调用init中统一发送函数
        success = await self.hass.async_add_executor_job(self._device.send_command, command)
        if success:
            # 更新当前选择项
            self._attr_current_option = option
            # 更新实体状态
            self.async_write_ha_state()
            _LOGGER.debug("Command executed: %s", option)
        else:
            _LOGGER.warning("Command failed: %s", option)

        @property
        def icon(self) -> str:
            """实体图标"""

            return "mid:remote"

        @property
        def extra_state_attributes(self) -> dict[str, int]:
            """附加属性
            用于显示支持的命令数量
            """

            return {"supported_commands": len(COMMAND_MAP)}