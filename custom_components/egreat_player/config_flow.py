"""Config flow for the Egreat Player integration."""

import logging
import voluptuous as vol
import serial
import serial.tools.list_ports
import time
import asyncio

from typing import Any
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from .const import DOMAIN, CONF_PORT, CONF_BAUDRATE, CMD_STATUS

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
        # print(serial.tools.list_ports.comports())
        _LOGGER.info("Ports: %s", [p.device for p in ports])

        if not ports:
            errors["base"] = "no_ports_found"
            return await self._show_manual_fallback()

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

    async def _show_manual_fallback(self, errors: dict[str, Any] | None = None) -> ConfigFlowResult:
        # 未自动识别到时，需要手动选择
        return await self.async_step_manual()

    def _is_likely_serial_device(self, port) -> bool:
        # 检测是否是串口设备
        # 排除蓝牙，调制解调器等
        exclude_keywords = ["Bluetooth", "Modem", "Fax", "Keyboard", "Mouse"]
        for keyword in exclude_keywords:
            if keyword in port.description:
                _LOGGER.debug("Excluding %s due to keyword: %s", port.device, keyword)
                return False

            # 优先选择USB串口设备
        if "USB" in port.description or "UART" in port.description:
            _LOGGER.debug("Including %s as USB/UART device", port.device)
            return True

        # 根据VID/PID判断（常见USB转串口芯片）
        # FTDI: 0x0403, Silicon Labs: 0x10C4, Prolific: 0x067B, CH340: 0x1A86
        if port.vid in [0x0403, 0x10C4, 0x067B, 0X1A86]:
            _LOGGER.debug("Including %s based on VID/PID", port.device)
            return True

        # 如果是Linux的串口，也进行测试
        if port.device.startswith("/dev/ttyS") or port.device.startswith("/dev/ttyACM"):
            _LOGGER.debug("Including %s as standard serial port", port.device)
            return True

        _LOGGER.debug("Excluding %s - no criteria matched", port.device)
        return False

    async def _test_port(self, port) -> bool:
        # 测试端口连接的是否是亿格瑞播放器
        try:
            result = await self.hass.async_add_executor_job(
                self._sync_test_port, port, 9600
            )
            if result:
                _LOGGER.info("Port %s responded, identified as Egreat Player", port)
                return True
        except Exception as e:
            _LOGGER.debug("Error testing %s: %s", port, e)

        return False

    def _sync_test_port(self, port: str, baudrate: int) -> bool:
        # 同步执行的端口测试
        try:
