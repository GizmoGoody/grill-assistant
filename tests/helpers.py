"""Probe devices for the tests, as another integration would create them."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

TEMPERATURE = {"unit_of_measurement": "°F", "device_class": "temperature"}


def _source(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain="thermoworks_cloud")
    entry.add_to_hass(hass)
    return entry


def rfx_meat(hass: HomeAssistant, name: str = "Probe", serial: str = "M1") -> tuple[str, list[str]]:
    """A ThermoWorks RFX MEAT: channel 0 (its core), channels 1 to 4 and an alarm threshold.

    Returns the device and its channels 0 to 4.
    """
    source = _source(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=source.entry_id,
        identifiers={("thermoworks_cloud", serial)},
        manufacturer="ThermoWorks",
        model="rfx meat",
        name=name,
    )
    registry = er.async_get(hass)
    channels = [
        registry.async_get_or_create(
            "sensor",
            "thermoworks_cloud",
            f"thermoworks_cloud-{serial}-{n}",
            config_entry=source,
            device_id=device.id,
            original_device_class="temperature",
            suggested_object_id=f"{name}_ch{n}",
        ).entity_id
        for n in range(5)
    ]
    registry.async_get_or_create(
        "sensor",
        "thermoworks_cloud",
        f"thermoworks_cloud-{serial}-1-high-alarm-threshold",
        config_entry=source,
        device_id=device.id,
        original_device_class="temperature",
    )
    return device.id, channels


def other_probe(hass: HomeAssistant, name: str, sensors: int) -> tuple[str, list[str]]:
    """A device of another brand with this many temperature sensors."""
    source = _source(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=source.entry_id, identifiers={("other", name)}, manufacturer="Other", model="probe", name=name
    )
    registry = er.async_get(hass)
    entities = [
        registry.async_get_or_create(
            "sensor",
            "other",
            f"{name}-{n}",
            config_entry=source,
            device_id=device.id,
            original_device_class="temperature",
            suggested_object_id=f"{name}_{n}",
        ).entity_id
        for n in range(sensors)
    ]
    return device.id, entities
