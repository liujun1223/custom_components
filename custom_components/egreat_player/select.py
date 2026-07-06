"""Select platform for Egreat Player!"""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EgreatPlayer, EgreatPlayerConfigEntry
from .const import COMMAND_MAP, DOMAIN, IP_CMD_MAP

_LOGGER = logging.getLogger(__name__)
PLACEHOLDER = "-选择命令-"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EgreatPlayerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """创建select实体!"""

    player: EgreatPlayer = entry.runtime_data
    async_add_entities([EgreatCommandSelect(entry.entry_id, player)])


class EgreatCommandSelect(SelectEntity):
    """Egreat 命令选择器.

    用于调试和快速发送遥控器命令.
    用户在 Home Assistant 前端选择某个命令后,
    会立即通过串口发送对应协议.
    """

    _attr_should_poll = False

    def __init__(self, entry_id: str, device: EgreatPlayer) -> None:
        """初始化实体!"""

        self._device = device
        self._entry_id = entry_id
        self._attr_name = "Remote"
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry_id}_command"
        if device._host:
            self._attr_options = [PLACEHOLDER] + list(IP_CMD_MAP.keys())
        else:
            self._attr_options = [PLACEHOLDER] + list(COMMAND_MAP.keys())
        self._attr_current_option = PLACEHOLDER

    @property
    def available(self) -> bool:
        """设备是否在线!"""

        return self._device.available

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

    async def async_select_option(self, option: str) -> None:
        """用户选择某个命令后执行.

        例如：
        home
        menu
        back
        play
        pause
        选择后立即发送串口命令.
        """

        if option == PLACEHOLDER:
            return

        _LOGGER.debug("Send command: %s", option)
        success = False

        # 优先走IP控制
        if self._device._host:
            ip_cmd = IP_CMD_MAP.get(option)
            if ip_cmd:
                success = await self.hass.async_add_executor_job(
                    self._device.send_ip_command, ip_cmd
                )
                if success:
                    _LOGGER.info("IP command executed: %s", option)
        # 降级到串口
        if not success:
            serial_cmd = COMMAND_MAP.get(option)
            if serial_cmd is None:
                _LOGGER.debug("Unknown command: %s", option)
                return
            success = await self.hass.async_add_executor_job(
                self._device.send_command, serial_cmd
            )
            if success:
                _LOGGER.info("Command executed: %s", option)
            else:
                _LOGGER.info("Command failed: %s", option)
        if success:
            self._attr_current_option = PLACEHOLDER
            self.async_write_ha_state()

    @property
    def icon(self) -> str:
        """实体图标!"""

        return "mdi:remote"

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """用于显示支持的命令数量!"""
        if self._device._host:
            return {"supported_commands": len(IP_CMD_MAP)}
        return {"supported_commands": len(COMMAND_MAP)}
