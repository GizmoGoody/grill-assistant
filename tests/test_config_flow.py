"""Adding a grill, then probes to it."""

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sous_chef.const import DOMAIN

from .helpers import TEMPERATURE, other_probe, rfx_meat


async def _grill(hass: HomeAssistant) -> MockConfigEntry:
    hass.states.async_set("sensor.grill_ambient", "250", TEMPERATURE)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Terrace grill", "grill_sensors": ["sensor.grill_ambient"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    return result["result"]


async def _add_probe(hass: HomeAssistant, entry: MockConfigEntry, user_input: dict):
    result = await hass.config_entries.subentries.async_init((entry.entry_id, "probe"), context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)


async def test_grill_and_its_options(hass: HomeAssistant) -> None:
    entry = await _grill(hass)
    assert entry.title == "Terrace grill"
    assert entry.options == {"grill_sensors": ["sensor.grill_ambient"], "keep_last": True}

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"grill_sensors": [], "keep_last": False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"grill_sensors": [], "keep_last": False}


async def test_known_probe_needs_only_the_device(hass: HomeAssistant) -> None:
    entry = await _grill(hass)
    device, channels = rfx_meat(hass, "RFX Probe Red")
    result = await _add_probe(hass, entry, {"device": device, "colors": ["red", "black"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    (subentry,) = entry.subentries.values()
    assert subentry.title == "RFX Probe Red"
    # The core (channel 0) is the reading, channels 1 to 4 run from the tip, and the alarm threshold is left out
    assert subentry.data == {
        "device": device,
        "reading": channels[0],
        "channels": channels[1:],
        "colors": ["red", "black"],
        "auto_on": True,
    }

    # The same probe cannot be added twice
    result = await _add_probe(hass, entry, {"device": device})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"device": "already_added"}


async def test_probe_with_one_sensor(hass: HomeAssistant) -> None:
    entry = await _grill(hass)
    device, (sensor,) = other_probe(hass, "Wired", 1)
    result = await _add_probe(hass, entry, {"device": device})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    (subentry,) = entry.subentries.values()
    assert subentry.data == {"device": device, "reading": sensor, "channels": [], "colors": [], "auto_on": False}


async def test_probe_with_several_sensors(hass: HomeAssistant) -> None:
    entry = await _grill(hass)
    device, sensors = other_probe(hass, "Multi", 3)
    result = await _add_probe(hass, entry, {"device": device, "colors": ["blue"]})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sensors"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"reading": sensors[1], "channels": [sensors[2], sensors[1], sensors[0]], "auto_on": True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    (subentry,) = entry.subentries.values()
    # The reading is left out of the sensors from the tip
    assert subentry.data == {
        "device": device,
        "reading": sensors[1],
        "channels": [sensors[2], sensors[0]],
        "colors": ["blue"],
        "auto_on": True,
    }


async def test_device_with_no_temperature(hass: HomeAssistant) -> None:
    entry = await _grill(hass)
    device, _ = other_probe(hass, "Empty", 0)
    result = await _add_probe(hass, entry, {"device": device})
    assert result["errors"] == {"device": "no_temperature"}
