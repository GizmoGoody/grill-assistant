"""The preset charts, as the Sous Chef Card reads them."""

from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.sous_chef.const import DOMAIN


async def test_charts(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    hass.config.country = "CA"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={"keep_last": True},
        subentries_data=[
            ConfigSubentryData(
                data={"name": "Brisket", "icon": "mdi:cow", "levels": [{"name": "Probe tender", "temperature": 203}], "unit": "°F"},
                subentry_type="food",
                title="Brisket",
                unique_id=None,
            )
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "sous_chef/charts"})
    response = await client.receive_json()
    assert response["success"]
    sources = response["result"]["sources"]
    # The country's chart first, the user's own foods last
    assert [s["key"] for s in sources] == ["health_canada", "thermoworks", "foodsafety_gov", "uk_fsa", "fsanz", "mine"]
    canada = sources[0]
    assert canada["government"] is True
    assert canada["countries"] == ["CA"]
    assert canada["url"].startswith("https://www.canada.ca/")
    poultry = next(f for f in canada["foods"] if f["key"] == "poultry")
    assert poultry["icon"] == "mdi:food-drumstick"
    assert poultry["levels"] == [{"key": "pieces", "f": 165, "c": 74}, {"key": "whole", "f": 180, "c": 82}]
    us_beef = next(f for f in sources[2]["foods"] if f["key"] == "beef")
    assert us_beef["levels"] == [{"key": "safe_minimum", "f": 145, "c": 63, "rest_minutes": 3}]
    # Other is no food of a chart
    assert all(f["key"] != "other" for s in sources for f in s["foods"])
    (brisket,) = sources[-1]["foods"]
    assert brisket == {"key": "Brisket", "icon": "mdi:cow", "levels": [{"key": "Probe tender", "f": 203.0, "c": 95.0}]}
    assert sources[-1]["url"] is None


async def test_charts_before_setup(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "sous_chef/charts"})
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "not_found"
