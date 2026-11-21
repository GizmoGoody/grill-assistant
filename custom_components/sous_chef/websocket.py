"""The preset charts, for the Sous Chef Card's chart view.

Entities carry only the chosen source's foods and levels. This command gives
every source's whole chart, in the order the Source select lists them, so a
card can show a chart and set a probe from it.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.icon import async_get_icons

from .const import DOMAIN
from .presets import MINE, OTHER, Catalog


@callback
def async_setup(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_charts)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/charts"})
@websocket_api.async_response
async def ws_charts(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Every source's chart: its foods, each with its icon and its doneness levels."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Sous Chef is not set up")
        return
    icons = await async_get_icons(hass, "entity", [DOMAIN])
    food_icons = icons.get(DOMAIN, {}).get("select", {}).get("food_type", {}).get("state", {})
    connection.send_result(msg["id"], {"sources": charts(entries[0].runtime_data.catalog, food_icons)})


def charts(catalog: Catalog, food_icons: dict[str, str]) -> list[dict[str, Any]]:
    """The catalog as plain data. Foods of the user's own take their own icons."""
    return [
        {
            "key": source.key,
            "url": source.url,
            "government": source.government,
            "countries": list(source.countries),
            "foods": [
                {
                    "key": food,
                    "icon": catalog.icons.get(food) if source.key == MINE else food_icons.get(food),
                    "levels": [
                        {
                            "key": key,
                            "f": level.f,
                            "c": level.c,
                            **({"rest_minutes": level.rest_minutes} if level.rest_minutes else {}),
                            **({"hold_minutes": level.hold_minutes} if level.hold_minutes else {}),
                        }
                        for key, level in catalog.levels(source.key, food).items()
                    ],
                }
                for food in catalog.foods(source.key)
                if food != OTHER
            ],
        }
        for source in catalog.sources.values()
    ]
