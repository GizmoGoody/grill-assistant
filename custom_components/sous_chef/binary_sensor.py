"""Whether a probe is done, stalled or out of range, and whether an ambient sensor is out of range."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SousChefConfigEntry
from .entity import AmbientEntity, ProbeEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: SousChefConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for subentry_id, probe in entry.runtime_data.probes.items():
        subentry = entry.subentries[subentry_id]
        async_add_entities(
            [
                DoneBinarySensor(hass, subentry, probe, "done"),
                StalledBinarySensor(hass, subentry, probe, "stalled"),
                ProbeAlarmBinarySensor(hass, subentry, probe, "alarm"),
            ],
            config_subentry_id=subentry_id,
        )
    for subentry_id, ambient in entry.runtime_data.ambients.items():
        async_add_entities(
            [AmbientAlarmBinarySensor(hass, entry.subentries[subentry_id], ambient, "alarm")],
            config_subentry_id=subentry_id,
        )


class DoneBinarySensor(ProbeEntity, BinarySensorEntity):
    """On once the internal temperature reaches the target, less Pull early by."""

    @property
    def available(self) -> bool:
        return self.probe.cooking

    @property
    def is_on(self) -> bool:
        return self.probe.done


class StalledBinarySensor(ProbeEntity, BinarySensorEntity):
    """On while the internal temperature has stopped rising short of the target."""

    @property
    def available(self) -> bool:
        return self.probe.cooking

    @property
    def is_on(self) -> bool:
        return self.probe.stalled


class ProbeAlarmBinarySensor(ProbeEntity, BinarySensorEntity):
    """On while the probe is on and its internal temperature is above Alarm high or below Alarm low."""

    @property
    def available(self) -> bool:
        return self.probe.active

    @property
    def is_on(self) -> bool:
        return self.probe.alarm


class AmbientAlarmBinarySensor(AmbientEntity, BinarySensorEntity):
    """On while the ambient temperature is above Alarm high or below Alarm low.

    Its sensor attribute tells the Sous Chef Card which sensor this is.
    """

    _unrecorded_attributes = frozenset({"sensor"})

    @property
    def is_on(self) -> bool:
        return self.ambient.alarm

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"sensor": self.ambient.sensor}
