"""Config flow for the Egreat Player integration."""

import logging
import voluptuous as vol
import serial
import serial.tools.list_ports
import time

from typing import Any
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_BAUDRATE,
    CONF_HOST,
    CMD_STATUS,
    SUPPORTED_USB_VIDS,
    DEFAULT_BAUDRATE,
    RESPONSE_HEADER
)

_LOGGER = logging.getLogger(__name__)

class EgreatPlayerConfigFlow(config_entries.ConfigFlow, domain = DOMAIN):
    """Handle a config flow for Egreat player."""
    # 初始化亿格瑞播放器配置流程

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        # 处理初始的步骤
        # 让用户选择自动识别还是手动选择
        if user_input is not None:
            # 自动扫描
            if user_input.get("auto_detect"):
                return await self.async_step_auto_detect()
            # 手动选择
            return await self.async_step_manual()

        return self.async_show_form(
            step_id = "user",
            data_schema = vol.Schema({
                vol.Required("auto_detect", default = True): bool,
            })
        )

    async def async_step_auto_detect(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # 自动识别串口
        # 串口为/dev/ttys*

        # 获取所有串口
        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        _LOGGER.info("Available ports: %s", [p.device for p in ports])

        # 没有发现串口
        if not ports:
            _LOGGER.debug("No Serial Ports Found")
            return await self.async_step_manual()

        test_ports = [
            port.device for port in ports if self._is_likely_serial_device(port)
        ]
        _LOGGER.info("Candidate ports: %s", test_ports)

        # 没有可测试的设备
        if not test_ports:
            return await self.async_step_manual()

        # 查找设备成功
        for port in test_ports:
            _LOGGER.debug("Testing port: %s", port)
            try:
                valid = await self._test_port(port)
            except Exception as e:
                _LOGGER.debug("Failed testing %s: %s", port, e)
                continue
            if not valid:
                continue
            _LOGGER.info("Found Egreat Player on port: %s", port)

            # 防止重复添加
            await self.async_set_unique_id(port)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title = "K5",
                data = {
                    CONF_PORT: port,
                    CONF_BAUDRATE: DEFAULT_BAUDRATE,
                    CONF_HOST: ""
                }
            )

        _LOGGER.debug("Auto detection failed")

        # 自动扫描失败，进入手动模式
        return await self.async_step_manual()

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # 手动选择
        errors = {}

        # 获取串口列表
        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        _LOGGER.info("Ports: %s", [p.device for p in ports])

        port_options = {
            port.device: f"{port.device} - {port.description}" for port in ports
        }

        # 用户提交
        if user_input is not None:
            port = user_input[CONF_PORT]
            # 验证设备
            valid = await self._test_port(port)

            if not valid:
                errors["base"] = "no_device_found"
            else:
                # 防止重复添加
                await self.async_set_unique_id(port)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title = "K5",
                    data = user_input
                )

        return self.async_show_form(
            step_id = "manual",
            data_schema = vol.Schema({
                vol.Required(CONF_PORT, default = user_input.get(CONF_PORT, "")): vol.In(port_options),
                vol.Required(CONF_BAUDRATE, default = user_input.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)): vol.In([2400, 4800, 9600, 19200, 38400, 57600, 115200]),
                vol.Optional(CONF_HOST, default = user_input.get(CONF_HOST, "")): str
            }),
            errors = errors
        )

    def _is_likely_serial_device(self, port) -> bool:
        # 检测是否是串口设备
        # 排除蓝牙，调制解调器等

        _LOGGER.debug(
            "Port=%s VID=%s PID=%s DESC=%s",
            port.device,
            hex(port.vid) if port.vid else None,
            hex(port.pid) if port.pid else None,
            port.description,
        )

        exclude_keywords = ["Bluetooth", "Modem", "Fax", "Keyboard", "Mouse"]

        # 排除明显无关设备
        if any(
            keyword in port.description
            for keyword in exclude_keywords
        ):
            return False

        # VID白名单
        if port.vid in SUPPORTED_USB_VIDS:
            return True

        # 常见USB串口
        if "USB" in port.description or "UART" in port.description:
            return True

        # Linux常见串口
        if port.device.startswith("/dev/ttyUSB") or port.device.startswith("/dev/ttyS"):
            return True

        return False

    async def _test_port(self, port: str) -> bool:
        # 异步测试串口

        try:
            result = await self.hass.async_add_executor_job(
                self._sync_test_port, port
            )
            return result
        except Exception as e:
            _LOGGER.debug("Error testing %s: %s", port, e)
            return False

    def _sync_test_port(self, port: str) -> bool:
        # 同步执行的端口测试
        try:
            with serial.Serial(port, DEFAULT_BAUDRATE, timeout = 1) as ser:
                # 等待串口稳定
                time.sleep(0.2)
                # 清空缓冲区
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                # 发送状态查询命令
                ser.write(CMD_STATUS)
                # 等待设备响应
                time.sleep(0.3)
                response = ser.read(20)
                _LOGGER.debug("Port %s response: %s", port, response.hex())

                # 验证协议响应
                if not response:
                    return False
                return response[0] == RESPONSE_HEADER
        except Exception as e:
            _LOGGER.debug("Failed to test %s: %s", port, e)
            return False