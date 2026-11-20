"""The entities of a probe."""

from __future__ import annotations

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity

from .probe import Probe


class ProbeEntity(Entity):
    """An entity of a probe's cook.

    It sits on the probe's own device (a ThermoWorks RFX probe, for example),
    as Home Assistant's helpers sit on their source's device, so the probe's
    readings and its cook are found together.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, subentry: ConfigSubentry, probe: Probe, key: str) -> None:
        self.probe = probe
        self._attr_translation_key = key
        self._attr_unique_id = f"{subentry.subentry_id}_{key}"
        self.device_entry = dr.async_get(hass).async_get(probe.device_id)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.probe.async_add_listener(self.async_write_ha_state))
