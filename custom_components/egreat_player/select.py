"""select platform for Egreat Player"""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EgreatPlayer, EgreatPlayerConfigEntry
from .remote import COMMAND_MAP

_LOGGER = logging(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: EgreatPlayerConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """创建select实体"""

    player: EgreatPlayer = entry.runtime_data

    async_add_entities([EgreatCommandSelect(entry.entry_id, player)])

class EgreatCommandSelect(SelectEntity):
    """Egreat 命令选择器
    """