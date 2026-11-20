"""Whether a probe is on: a cook runs while it is."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .entity import ProbeEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GrillConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for subentry_id, probe in entry.runtime_data.items():
        async_add_entities(
            [ActiveSwitch(hass, entry.subentries[subentry_id], probe, "active")], config_subentry_id=subentry_id
        )


class ActiveSwitch(ProbeEntity, SwitchEntity):
    """On while the probe is in use. Turning it on starts a new cook."""

    @property
    def is_on(self) -> bool:
        return self.probe.active

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.probe.set_active(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.probe.set_active(False)
