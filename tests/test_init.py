"""One probe and one ambient sensor: the cook follows the Active switch, the presets and the internal temperature."""

from collections import deque

from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sous_chef.const import DOMAIN

from .helpers import TEMPERATURE, other_probe, rfx_meat, rfx_state

ACTIVE = "switch.probe_active"
SOURCE = "select.probe_source"
FOOD = "select.probe_food_type"
DONENESS = "select.probe_doneness"
TARGET = "number.probe_target"


async def _setup(
    hass: HomeAssistant,
    reading: str = "100",
    keep_last: bool = True,
    minutes_ago: float = 0,
    country: str | None = "US",
    extra: list[ConfigSubentryData] | None = None,
) -> tuple[MockConfigEntry, list[str]]:
    hass.config.units = US_CUSTOMARY_SYSTEM
    hass.config.country = country
    device, channels = rfx_meat(hass)
    hass.states.async_set(channels[0], reading, rfx_state(minutes_ago))
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sous Chef",
        data={},
        options={"keep_last": keep_last},
        subentries_data=[
            ConfigSubentryData(
                data={
                    "device": device,
                    "internal": channels[0],
                    "channels": channels[1:],
                    "colors": ["red", "blue"],
                    "auto_on": True,
                },
                subentry_type="probe",
                title="Probe",
                unique_id=None,
            ),
            *(extra or []),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, channels


async def _read(hass: HomeAssistant, entity_id: str, value: str, minutes_ago: float = 0) -> None:
    hass.states.async_set(entity_id, value, rfx_state(minutes_ago))
    await hass.async_block_till_done()


async def _switch(hass: HomeAssistant, on: bool) -> None:
    await hass.services.async_call("switch", "turn_on" if on else "turn_off", {"entity_id": ACTIVE}, blocking=True)


async def _select(hass: HomeAssistant, entity_id: str, option: str) -> None:
    await hass.services.async_call("select", "select_option", {"entity_id": entity_id, "option": option}, blocking=True)


async def _set(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call("number", "set_value", {"entity_id": entity_id, "value": value}, blocking=True)


def _value(hass: HomeAssistant, entity_id: str) -> float:
    return float(hass.states.get(entity_id).state)


async def test_entities_on_the_probe_device(hass: HomeAssistant) -> None:
    _, channels = await _setup(hass)
    assert hass.states.get(ACTIVE).state == "off"
    attributes = hass.states.get("sensor.probe_progress").attributes
    assert attributes["internal"] == "sensor.probe_ch0"
    assert attributes["channels"] == ["sensor.probe_ch1", "sensor.probe_ch2", "sensor.probe_ch3", "sensor.probe_ch4"]
    assert attributes["colors"] == ["red", "blue"]
    # Max is the highest channel, whichever it is
    for channel, value in zip(channels[1:], ("91", "88", "103", "94"), strict=True):
        await _read(hass, channel, value)
    assert _value(hass, "sensor.probe_max") == 103


async def test_sources_for_the_country(hass: HomeAssistant) -> None:
    await _setup(hass)
    state = hass.states.get(SOURCE)
    # The country's government chart comes first, and is a new probe's source; Mine is last
    assert state.state == "foodsafety_gov"
    assert state.attributes["options"][0] == "foodsafety_gov"
    assert state.attributes["options"][1] == "thermoworks"
    assert state.attributes["options"][-1] == "mine"
    assert state.attributes["url"].startswith("https://www.foodsafety.gov/")
    await _select(hass, FOOD, "beef")
    assert hass.states.get(DONENESS).state == "safe_minimum"
    assert _value(hass, TARGET) == 145
    assert hass.states.get(DONENESS).attributes["rest_minutes"] == 3


async def test_sources_elsewhere(hass: HomeAssistant) -> None:
    await _setup(hass, country="NZ")
    assert hass.states.get(SOURCE).state == "fsanz"
    assert hass.states.get(FOOD).attributes["options"] == ["ground_meat", "poultry", "other"]


async def test_preset_sets_target(hass: HomeAssistant) -> None:
    await _setup(hass)
    await _select(hass, SOURCE, "thermoworks")
    await _select(hass, FOOD, "beef")
    # The first doneness of the food, and its target
    assert hass.states.get(DONENESS).state == "rare"
    assert _value(hass, TARGET) == 120
    await _select(hass, DONENESS, "medium_rare")
    assert _value(hass, TARGET) == 130


async def test_preset_in_celsius(hass: HomeAssistant) -> None:
    hass.config.units = METRIC_SYSTEM
    hass.config.country = None
    device, (sensor,) = other_probe(hass, "Probe", 1)
    hass.states.async_set(sensor, "20", {"unit_of_measurement": "°C", "device_class": "temperature"})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={"keep_last": True},
        subentries_data=[
            ConfigSubentryData(
                data={"device": device, "internal": sensor, "channels": [], "colors": [], "auto_on": False},
                subentry_type="probe",
                title="Probe",
                unique_id=None,
            )
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # With no country, the brand chart comes first
    assert hass.states.get(SOURCE).state == "thermoworks"
    await _select(hass, FOOD, "beef")
    # The chart's own °C value, not a conversion
    assert _value(hass, TARGET) == 49
    # One sensor: no channels, so no Max
    assert hass.states.get("sensor.probe_max") is None


async def test_custom_target(hass: HomeAssistant) -> None:
    await _setup(hass)
    await _select(hass, SOURCE, "thermoworks")
    await _select(hass, FOOD, "pork")
    assert hass.states.get(DONENESS).state == "usda_done"
    await _set(hass, TARGET, 148)
    assert hass.states.get(DONENESS).state == "custom"
    # A level's own target names its doneness again
    await _set(hass, TARGET, 150)
    assert hass.states.get(DONENESS).state == "well_done"


async def test_switching_source_keeps_the_food(hass: HomeAssistant) -> None:
    await _setup(hass)
    await _select(hass, SOURCE, "thermoworks")
    await _select(hass, FOOD, "beef")
    await _select(hass, DONENESS, "medium_rare")
    await _select(hass, SOURCE, "health_canada")
    assert hass.states.get(FOOD).state == "beef"
    assert hass.states.get(DONENESS).state == "medium_rare"
    assert _value(hass, TARGET) == 145
    # A source without the food: Other, and the target stays
    await _select(hass, SOURCE, "fsanz")
    assert hass.states.get(FOOD).state == "other"
    assert hass.states.get(DONENESS).state == "custom"
    assert _value(hass, TARGET) == 145


async def test_foods_of_your_own(hass: HomeAssistant) -> None:
    brisket = ConfigSubentryData(
        data={
            "name": "Brisket",
            "icon": "mdi:cow",
            "levels": [{"name": "Probe tender", "temperature": 95}],
            "unit": "°C",
        },
        subentry_type="food",
        title="Brisket",
        unique_id=None,
    )
    await _setup(hass, extra=[brisket])
    await _select(hass, SOURCE, "mine")
    assert hass.states.get(FOOD).attributes["options"] == ["Brisket", "other"]
    await _select(hass, FOOD, "Brisket")
    assert hass.states.get(FOOD).attributes["icon"] == "mdi:cow"
    assert hass.states.get(DONENESS).state == "Probe tender"
    assert _value(hass, TARGET) == 203
    assert hass.states.get(SOURCE).attributes["url"] is None


async def test_start_is_the_lowest_reading(hass: HomeAssistant) -> None:
    _, channels = await _setup(hass, "84")
    reading = channels[0]
    # The cook can be set up before the probe is turned on
    await _select(hass, FOOD, "poultry")
    assert hass.states.get("sensor.probe_progress").state == "unknown"
    assert hass.states.get("binary_sensor.probe_done").state == "unavailable"
    await _switch(hass, True)
    # In the air it reads 84 °F. In the food it falls to 39 °F, the cook's start.
    await _read(hass, reading, "39")
    assert hass.states.get("sensor.probe_progress").attributes["start"] == 39
    await _read(hass, reading, "102")
    assert round(_value(hass, "sensor.probe_progress")) == 50
    assert hass.states.get("binary_sensor.probe_done").state == "off"
    # Pull early by 5 °F: done at 160 °F
    await _set(hass, "number.probe_pull_early_by", 5)
    await _read(hass, reading, "160")
    assert hass.states.get("binary_sensor.probe_done").state == "on"
    # Turned off, the cook ends
    await _switch(hass, False)
    assert hass.states.get("binary_sensor.probe_done").state == "unavailable"
    assert hass.states.get("sensor.probe_progress").state == "unknown"


async def test_probe_alarm(hass: HomeAssistant) -> None:
    _, channels = await _setup(hass, "39")
    reading = channels[0]
    alarm = "binary_sensor.probe_alarm"
    assert hass.states.get(alarm).state == "unavailable"
    await _switch(hass, True)
    await _set(hass, "number.probe_alarm_low", 140)
    await _set(hass, "number.probe_alarm_high", 200)
    # Below Alarm low before it ever got there: no alarm
    assert hass.states.get(alarm).state == "off"
    await _read(hass, reading, "150")
    await _read(hass, reading, "135")
    assert hass.states.get(alarm).state == "on"
    await _read(hass, reading, "150")
    assert hass.states.get(alarm).state == "off"
    await _read(hass, reading, "201")
    assert hass.states.get(alarm).state == "on"
    # 0 is no limit
    await _set(hass, "number.probe_alarm_high", 0)
    assert hass.states.get("number.probe_alarm_high").state == "unknown"
    assert hass.states.get(alarm).state == "off"


async def test_ambient_alarm(hass: HomeAssistant) -> None:
    device, (sensor,) = other_probe(hass, "Gateway", 1)
    hass.states.async_set(sensor, "70", TEMPERATURE)
    ambient = ConfigSubentryData(
        data={"device": device, "sensor": sensor}, subentry_type="ambient", title="Grill Ambient", unique_id=None
    )
    await _setup(hass, extra=[ambient])
    alarm = "binary_sensor.gateway_alarm"
    assert hass.states.get(alarm).attributes["sensor"] == sensor
    await _set(hass, "number.gateway_alarm_low", 225)
    await _set(hass, "number.gateway_alarm_high", 275)
    # The grill is being lit: no alarm until it first gets to 225 °F
    assert hass.states.get(alarm).state == "off"
    hass.states.async_set(sensor, "250", TEMPERATURE)
    await hass.async_block_till_done()
    hass.states.async_set(sensor, "219", TEMPERATURE)
    await hass.async_block_till_done()
    assert hass.states.get(alarm).state == "on"
    hass.states.async_set(sensor, "280", TEMPERATURE)
    await hass.async_block_till_done()
    assert hass.states.get(alarm).state == "on"
    hass.states.async_set(sensor, "250", TEMPERATURE)
    await hass.async_block_till_done()
    assert hass.states.get(alarm).state == "off"


async def test_rate_window(hass: HomeAssistant) -> None:
    entry, _ = await _setup(hass)
    (probe,) = entry.runtime_data.probes.values()
    probe.active = True
    now = dt_util.utcnow().timestamp()
    # A sear: 5 °F a minute. The window shrinks to the last few minutes, so the rate is the current one.
    probe._samples = deque((now - 60 * m, 200 - 5 * m) for m in range(15, -1, -1) if m < 5 or m > 10)
    assert round(probe.rate, 1) == 5.0
    # A low smoke: a 0.1 °F step a minute apart does not swing it
    probe._samples = deque((now - 60 * m, 150.0 if m > 0 else 150.1) for m in range(15, -1, -1))
    assert abs(probe.rate) < 0.05
    # Too little time: no rate yet
    probe._samples = deque((now - 30 * m, 100.0) for m in range(3, -1, -1))
    assert probe.rate is None


async def test_turns_on_when_it_starts_reporting(hass: HomeAssistant) -> None:
    _, channels = await _setup(hass, "unavailable")
    assert hass.states.get(ACTIVE).state == "off"
    await _read(hass, channels[0], "84")
    assert hass.states.get(ACTIVE).state == "on"


async def test_charger_value_is_no_reading(hass: HomeAssistant) -> None:
    # On its charger, an RFX probe keeps showing its last value from days ago
    _, channels = await _setup(hass, "70", minutes_ago=3000)
    reading = channels[0]
    # A cloud blink brings the same old value back: the probe is not reporting, so it stays off
    await _read(hass, reading, "unavailable")
    await _read(hass, reading, "70", minutes_ago=3000)
    assert hass.states.get(ACTIVE).state == "off"
    await _switch(hass, True)
    assert hass.states.get("sensor.probe_progress").attributes["start"] is None
    # Off the charger it sends new data: that is its first reading
    await _read(hass, reading, "68")
    assert hass.states.get("sensor.probe_progress").attributes["start"] == 68


async def test_off_the_charger_turns_it_on(hass: HomeAssistant) -> None:
    _, channels = await _setup(hass, "70", minutes_ago=3000)
    await _read(hass, channels[0], "71")
    assert hass.states.get(ACTIVE).state == "on"


async def test_signal_drop_keeps_the_cook(hass: HomeAssistant) -> None:
    _, channels = await _setup(hass, "39")
    reading = channels[0]
    await _switch(hass, True)
    await _select(hass, FOOD, "poultry")
    await _read(hass, reading, "80")
    await _read(hass, reading, "unavailable")
    await _read(hass, reading, "82")
    assert hass.states.get(ACTIVE).state == "on"
    assert hass.states.get("sensor.probe_progress").attributes["start"] == 39
    assert hass.states.get(FOOD).state == "poultry"


async def test_new_cook_keeps_the_last_settings(hass: HomeAssistant) -> None:
    await _setup(hass)
    await _switch(hass, True)
    await _select(hass, SOURCE, "thermoworks")
    await _select(hass, FOOD, "beef")
    await _switch(hass, False)
    await _switch(hass, True)
    assert hass.states.get(SOURCE).state == "thermoworks"
    assert hass.states.get(FOOD).state == "beef"
    assert _value(hass, TARGET) == 120


async def test_new_cook_starts_blank(hass: HomeAssistant) -> None:
    await _setup(hass, keep_last=False)
    await _switch(hass, True)
    await _select(hass, SOURCE, "thermoworks")
    await _select(hass, FOOD, "beef")
    await _switch(hass, False)
    await _switch(hass, True)
    assert hass.states.get(SOURCE).state == "foodsafety_gov"
    assert hass.states.get(FOOD).state == "other"
    assert hass.states.get(TARGET).state == "unknown"


async def test_cook_survives_reload(hass: HomeAssistant) -> None:
    entry, _ = await _setup(hass)
    await _switch(hass, True)
    await _select(hass, SOURCE, "thermoworks")
    await _select(hass, FOOD, "fish")
    await _set(hass, "number.probe_alarm_high", 150)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ACTIVE).state == "on"
    assert hass.states.get(FOOD).state == "fish"
    assert hass.states.get(DONENESS).state == "tuna_swordfish_marlin"
    assert _value(hass, "number.probe_alarm_high") == 150
