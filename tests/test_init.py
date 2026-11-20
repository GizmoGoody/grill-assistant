"""A grill with one probe: its cook follows its Active switch, its presets and its reading."""

from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grill_assistant.const import DOMAIN

from .helpers import TEMPERATURE, rfx_meat

ACTIVE = "switch.probe_active"


async def _setup(hass: HomeAssistant, reading: str = "100", keep_last: bool = True) -> tuple[MockConfigEntry, str]:
    hass.config.units = US_CUSTOMARY_SYSTEM
    device, channels = rfx_meat(hass)
    hass.states.async_set(channels[0], reading, TEMPERATURE)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Grill",
        data={},
        options={"grill_sensors": ["sensor.grill_ambient"], "keep_last": keep_last},
        subentries_data=[
            ConfigSubentryData(
                data={
                    "device": device,
                    "reading": channels[0],
                    "channels": channels[1:],
                    "colors": ["red", "blue"],
                    "auto_on": True,
                },
                subentry_type="probe",
                title="Probe",
                unique_id=None,
            )
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, channels[0]


async def _read(hass: HomeAssistant, entity_id: str, value: str) -> None:
    hass.states.async_set(entity_id, value, TEMPERATURE)
    await hass.async_block_till_done()


async def _switch(hass: HomeAssistant, on: bool) -> None:
    await hass.services.async_call("switch", "turn_on" if on else "turn_off", {"entity_id": ACTIVE}, blocking=True)


async def _select(hass: HomeAssistant, entity_id: str, option: str) -> None:
    await hass.services.async_call("select", "select_option", {"entity_id": entity_id, "option": option}, blocking=True)


async def test_entities_on_the_probe_device(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert hass.states.get(ACTIVE).state == "off"
    attributes = hass.states.get("sensor.probe_progress").attributes
    assert attributes["reading"] == "sensor.probe_ch0"
    assert attributes["channels"] == ["sensor.probe_ch1", "sensor.probe_ch2", "sensor.probe_ch3", "sensor.probe_ch4"]
    assert attributes["colors"] == ["red", "blue"]
    grill = hass.states.get("sensor.grill_active_probes")
    assert grill.state == "0"
    assert grill.attributes["grill_sensors"] == ["sensor.grill_ambient"]
    assert grill.attributes["probes"] == ["sensor.probe_progress"]


async def test_preset_sets_target(hass: HomeAssistant) -> None:
    await _setup(hass)
    await _select(hass, "select.probe_cook_type", "beef")
    # The first doneness of the type, and its target
    assert hass.states.get("select.probe_doneness").state == "rare"
    assert float(hass.states.get("number.probe_target").state) == 125
    await _select(hass, "select.probe_doneness", "medium_rare")
    assert float(hass.states.get("number.probe_target").state) == 135


async def test_custom_target(hass: HomeAssistant) -> None:
    await _setup(hass)
    await _select(hass, "select.probe_cook_type", "pork")
    await hass.services.async_call("number", "set_value", {"entity_id": "number.probe_target", "value": 150}, blocking=True)
    assert hass.states.get("select.probe_doneness").state == "custom"
    # A preset's own target names its doneness again
    await hass.services.async_call("number", "set_value", {"entity_id": "number.probe_target", "value": 160}, blocking=True)
    assert hass.states.get("select.probe_doneness").state == "well_done"


async def test_start_is_the_lowest_reading(hass: HomeAssistant) -> None:
    _, reading = await _setup(hass, "84")
    # The cook can be set up before the probe is turned on
    await _select(hass, "select.probe_cook_type", "poultry")
    assert hass.states.get("sensor.probe_progress").state == "unknown"
    assert hass.states.get("binary_sensor.probe_done").state == "unavailable"
    await _switch(hass, True)
    assert hass.states.get("sensor.grill_active_probes").state == "1"
    # In the air it reads 84 °F. In the meat it falls to 39 °F, the cook's start.
    await _read(hass, reading, "39")
    assert hass.states.get("sensor.probe_progress").attributes["start"] == 39
    await _read(hass, reading, "102")
    assert round(float(hass.states.get("sensor.probe_progress").state)) == 50
    assert hass.states.get("binary_sensor.probe_done").state == "off"
    await _read(hass, reading, "166")
    assert hass.states.get("binary_sensor.probe_done").state == "on"
    # Turned off, the cook ends
    await _switch(hass, False)
    assert hass.states.get("binary_sensor.probe_done").state == "unavailable"
    assert hass.states.get("sensor.probe_progress").state == "unknown"


async def test_turns_on_when_it_starts_reporting(hass: HomeAssistant) -> None:
    _, reading = await _setup(hass, "unavailable")
    assert hass.states.get(ACTIVE).state == "off"
    await _read(hass, reading, "84")
    assert hass.states.get(ACTIVE).state == "on"


async def test_signal_drop_keeps_the_cook(hass: HomeAssistant) -> None:
    _, reading = await _setup(hass, "39")
    await _switch(hass, True)
    await _select(hass, "select.probe_cook_type", "poultry")
    await _read(hass, reading, "80")
    await _read(hass, reading, "unavailable")
    await _read(hass, reading, "82")
    assert hass.states.get(ACTIVE).state == "on"
    assert hass.states.get("sensor.probe_progress").attributes["start"] == 39
    assert hass.states.get("select.probe_cook_type").state == "poultry"


async def test_new_cook_keeps_the_last_settings(hass: HomeAssistant) -> None:
    await _setup(hass)
    await _switch(hass, True)
    await _select(hass, "select.probe_cook_type", "beef")
    await _switch(hass, False)
    await _switch(hass, True)
    assert hass.states.get("select.probe_cook_type").state == "beef"
    assert float(hass.states.get("number.probe_target").state) == 125


async def test_new_cook_starts_blank(hass: HomeAssistant) -> None:
    await _setup(hass, keep_last=False)
    await _switch(hass, True)
    await _select(hass, "select.probe_cook_type", "beef")
    await _switch(hass, False)
    await _switch(hass, True)
    assert hass.states.get("select.probe_cook_type").state == "manual"
    assert hass.states.get("number.probe_target").state == "unknown"


async def test_cook_survives_reload(hass: HomeAssistant) -> None:
    entry, _ = await _setup(hass)
    await _switch(hass, True)
    await _select(hass, "select.probe_cook_type", "seafood")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ACTIVE).state == "on"
    assert hass.states.get("select.probe_cook_type").state == "seafood"
    assert hass.states.get("select.probe_doneness").state == "tuna"
