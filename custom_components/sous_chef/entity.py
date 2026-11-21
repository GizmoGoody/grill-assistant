"""The entities of a probe or an ambient sensor."""

from __future__ import annotations

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity

from .probe import Ambient, Probe


class SousChefEntity(Entity):
    """An entity of a probe or an ambient sensor.

    It sits on the probe's or sensor's own device (a ThermoWorks RFX probe,
    for example), as Home Assistant's helpers sit on their source's device, so
    the readings and what Sous Chef makes of them are found together.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, subentry: ConfigSubentry, followed: Probe | Ambient, key: str) -> None:
        self.followed = followed
        self._attr_translation_key = key
        self._attr_unique_id = f"{subentry.subentry_id}_{key}"
        self.device_entry = dr.async_get(hass).async_get(followed.device_id)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.followed.async_add_listener(self.async_write_ha_state))


class ProbeEntity(SousChefEntity):
    """An entity of a probe's cook."""

    followed: Probe

    @property
    def probe(self) -> Probe:
        return self.followed


class AmbientEntity(SousChefEntity):
    """An entity of an ambient sensor."""

    followed: Ambient

    @property
    def ambient(self) -> Ambient:
        return self.followed
