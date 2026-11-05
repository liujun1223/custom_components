"""pytest 全局配置：加载 Home Assistant 测试插件，并允许加载 custom_components 里的集成."""
import sys

import pytest

# HA 依赖 Linux 专有模块（fcntl），Windows 上无法加载该插件
if sys.platform != "win32":
    pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request):
    """让每个涉及 HA 的测试自动加载本仓库的 custom_components."""
    if sys.platform != "win32":
        enable_custom_integrations = request.getfixturevalue(
            "enable_custom_integrations"
        )
        yield enable_custom_integrations
    else:
        yield
