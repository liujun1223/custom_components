"""Config flow for the Egreat Player integration."""

import logging
import voluptuous as vol
import serial
import serial.tools.list_ports

from typing import Any
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN, CONF_PORT, CONF_BAUDRATE

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(ConfigFlow, domain = DOMAIN):
    """Handle a config flow for Egreat player."""
    # 初始化亿格瑞播放器配置流程

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        # 处理初始的步骤
        # 让用户选择自动识别还是手动选择
        if user_input is not None:
            if user_input.get("auto_detect"):
                return await self.async_step_auto_detect()
            return await self.async_step_manual()

        return self.async_show_form(
            step_id = "user",
            data_schema = vol.Schema({
                vol.Required("auto_detect", default = True): bool,
            }),
            description_placeholders = {
                "info": "选择[自动识别]将自动查找亿格瑞播放器"
            }
        )

    async def async_step_auto_detect(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # 自动识别串口
        # 串口为/dev/ttys*
        errors = {}
        detected_ports = []

        # 获取所有串口
        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        _LOGGER.info(serial.tools.list_ports.comports)
        _LOGGER.info("Ports: %s", [p.device for p in ports])

        if not ports:
            errors["base"] = "no_ports_found"
            return await self._show_manual_fallback(errors)

        # 对串口逐个测试
        for port in ports:
            if not self._is_likely_serial_device(port):
                continue
            _LOGGER.info("Test port: %s", port.device)
            if await self._test_port(port.device):
                detected_ports.append(port.device)
                _LOGGER.info("Found Egreat Player on port: %s", port.device)
                break

        # 根据结果处理
        if detected_ports:
            # 找到了，直接创建
            return self.async_create_entry(
                title = "Egreat Player",
                data = {
                    CONF_PORT: detected_ports[0],
                    CONF_BAUDRATE: 9600  # 默认波特率
                }
            )
        else:
            # 没找到，用手动配置
            errors["base"] = "no_device_found"
            return await self._show_manual_fallback(errors)

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # 手动选择
        errors = {}

        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        _LOGGER.info("Ports: %s", [p.device for p in ports])

        port_options = {
            port.device: f"{port.device} - {port.description}" for port in ports
        }

        if not port_options:
            port_options = {"/dev/ttyUSB0": "未检测到串口，请检查连接"}
            errors["base"] = "no_ports_found"

        if user_input is not None:
            return self.async_create_entry(
                title = "Egreat Player",
                data = user_input
            )

        return self.async_show_form(
            step_id = "manual",
            data_schema = vol.Schema({
                vol.Required(CONF_PORT): vol.In(port_options),
                vol.Required(CONF_BAUDRATE, default = 9600):vol.In([2400, 4800, 9600, 19200, 38400, 57600, 115200])
            }),
            errors = errors
        )

    async def _show_manual_fallback(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # 未自动识别到时，需要手动选择
        return await self.async_step_manual(user_input)

    def _is_likely_serial_device(self, port) -> bool:
        # 检测是否是串口设备
        exclude_keywords = ["Bluetooth", "Modem", "Fax", "keyboard"]
        return

    def _test_port(self, port) -> bool:
        # 测试串口
        return


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
