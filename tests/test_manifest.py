"""冒烟测试：确认开发环境可用、集成结构符合 HA 要求。"""
import json
from pathlib import Path

MANIFEST_PATH = (
    Path(__file__).parent.parent
    / "custom_components"
    / "egreat_player"
    / "manifest.json"
)


def test_manifest_matches_folder() -> None:
    """manifest 的 domain 必须与目录名一致，且带有版本号。"""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["domain"] == MANIFEST_PATH.parent.name
    assert manifest["version"]
    assert manifest["config_flow"] is True


def test_manifest_declares_pyserial() -> None:
    """串口依赖必须在 manifest 中声明，HA 才能自动安装。"""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert any("pyserial" in req for req in manifest["requirements"])
