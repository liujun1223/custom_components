"""冒烟测试：确认开发环境可用、集成结构符合 HA 要求."""
import json
from pathlib import Path

MANIFEST_PATH = (
    Path(__file__).parent.parent
    / "custom_components"
    / "egreat_player"
    / "manifest.json"
)


def test_manifest_matches_folder() -> None:
    """Manifest 的 domain 必须与目录名一致，且带有版本号."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["domain"] == MANIFEST_PATH.parent.name
    assert manifest["version"]
    assert manifest["config_flow"] is True


def test_manifest_declares_ssdp_discovery() -> None:
    """SSDP 发现必须声明 DLNA MediaRenderer，集成才会出现在“已发现”列表."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert any(
        "MediaRenderer" in matcher.get("st", "") for matcher in manifest["ssdp"]
    )
    # hassfest 要求：导入 ssdp 组件模块需声明 after_dependencies
    assert "ssdp" in manifest["after_dependencies"]
