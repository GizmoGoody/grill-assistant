"""How a probe device's temperature sensors are laid out.

Most probe devices have one temperature sensor, and that sensor is the
reading. A known probe is one whose layout is built in, so it needs no
questions: a ThermoWorks RFX MEAT reports its core as channel 0 (the lowest
of its four sensors) and its sensors as channels 1 to 4, with channel 1 at
the tip.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

THERMOWORKS = "thermoworks_cloud"


@dataclass(frozen=True)
class Layout:
    """A known probe's reading and its sensors, in order from the tip."""

    reading: str
    channels: list[str]


def temperature_sensors(hass: HomeAssistant, device_id: str) -> list[str]:
    """The enabled temperature sensors on a device."""
    return sorted(
        entry.entity_id
        for entry in er.async_entries_for_device(er.async_get(hass), device_id)
        if entry.domain == "sensor"
        and not entry.disabled_by
        and (entry.device_class or entry.original_device_class) == "temperature"
    )


def known_layout(hass: HomeAssistant, device_id: str) -> Layout | None:
    """The built-in layout of a known probe, or None for any other device."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    if (device.manufacturer or "").lower() == "thermoworks" and (device.model or "").lower() == "rfx meat":
        return _rfx_meat(hass, device_id)
    return None


def _rfx_meat(hass: HomeAssistant, device_id: str) -> Layout | None:
    # Each channel's temperature has the unique ID thermoworks_cloud-<serial>-<channel>.
    # The alarm thresholds add a suffix after the channel, so they do not match.
    channels: dict[int, str] = {}
    for entry in er.async_entries_for_device(er.async_get(hass), device_id):
        if entry.domain == "sensor" and entry.platform == THERMOWORKS and (
            match := re.fullmatch(r".+-(\d+)", entry.unique_id)
        ):
            channels[int(match.group(1))] = entry.entity_id
    if 0 not in channels:
        return None
    return Layout(reading=channels[0], channels=[channels[n] for n in (1, 2, 3, 4) if n in channels])
