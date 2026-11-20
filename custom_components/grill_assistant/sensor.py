"""How a probe's cook is coming along (progress, rate, when it is done), and how many probes are on."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .const import CONF_GRILL_SENSORS, DOMAIN
from .entity import ProbeEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GrillConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for subentry_id, probe in entry.runtime_data.items():
        subentry = entry.subentries[subentry_id]
        async_add_entities(
            [
                ProgressSensor(hass, subentry, probe, "progress"),
                RateSensor(hass, subentry, probe, "rate"),
                DoneAtSensor(hass, subentry, probe, "done_at"),
            ],
            config_subentry_id=subentry_id,
        )
    async_add_entities([ActiveProbesSensor(entry)])


class ProgressSensor(ProbeEntity, SensorEntity):
    """How far the reading has come from the cook's start to the target.

    Its attributes tell the Grill card which probe this is: the reading, the
    probe's own sensors in order from the tip, its colors and the cook's start.
    """

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    # They describe the probe, not the cook, so the recorder leaves them out
    _unrecorded_attributes = frozenset({"reading", "channels", "colors", "start"})

    @property
    def native_value(self) -> float | None:
        return self.probe.progress

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "reading": self.probe.reading_entity,
            "channels": self.probe.channels,
            "colors": self.probe.colors,
            "start": self.probe.start,
        }


class RateSensor(ProbeEntity, SensorEntity):
    """How fast the reading is rising, in degrees per minute."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    @property
    def native_unit_of_measurement(self) -> str:
        return f"{self.probe.unit}/min"

    @property
    def native_value(self) -> float | None:
        return None if (rate := self.probe.rate) is None else round(rate, 2)


class DoneAtSensor(ProbeEntity, SensorEntity):
    """When the reading will reach the target at its current rate."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        return self.probe.done_at


class ActiveProbesSensor(SensorEntity):
    """How many of the grill's probes are on, on the grill's own device.

    Its attributes tell the Grill card what is on the grill: the grill's own
    sensors, and each probe's progress sensor.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "active_probes"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _unrecorded_attributes = frozenset({"grill_sensors", "probes"})

    def __init__(self, entry: GrillConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_active_probes"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title)

    async def async_added_to_hass(self) -> None:
        for probe in self._entry.runtime_data.values():
            self.async_on_remove(probe.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> int:
        return sum(probe.active for probe in self._entry.runtime_data.values())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        registry = er.async_get(self.hass)
        progress = (registry.async_get_entity_id("sensor", DOMAIN, f"{probe_id}_progress") for probe_id in self._entry.runtime_data)
        return {
            "grill_sensors": list(self._entry.options.get(CONF_GRILL_SENSORS, [])),
            "probes": [entity_id for entity_id in progress if entity_id],
        }
