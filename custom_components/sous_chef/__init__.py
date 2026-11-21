"""Sous Chef: a cook for each food probe, and alarms for each ambient sensor.

One config entry holds your kit. Each probe, ambient sensor and food of your
own is a config subentry. The integration keeps every probe's cook (on or
off, source, food, doneness, target) and every limit as entities on the
probe's or sensor's own device, so every browser shows the same cook at once
and automations can use it. The Sous Chef Card (a separate repository) shows
them.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import CONF_KEEP_LAST, DOMAIN, PLATFORMS, SUBENTRY_AMBIENT, SUBENTRY_FOOD, SUBENTRY_PROBE
from .presets import Catalog
from .probe import Ambient, Probe, SettingsStore

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class SousChefData:
    """The entry's probes and ambient sensors, by subentry ID, and its presets."""

    store: SettingsStore
    catalog: Catalog
    probes: dict[str, Probe]
    ambients: dict[str, Ambient]


type SousChefConfigEntry = ConfigEntry[SousChefData]


async def async_setup_entry(hass: HomeAssistant, entry: SousChefConfigEntry) -> bool:
    """Set up the probes and ambient sensors."""
    store = SettingsStore(hass, entry.entry_id)
    await store.async_load()
    catalog = Catalog.build(
        hass.config.country,
        [dict(s.data) for s in entry.subentries.values() if s.subentry_type == SUBENTRY_FOOD],
    )
    keep_last = entry.options.get(CONF_KEEP_LAST, True)
    probes = {
        subentry_id: Probe(hass, store, subentry_id, dict(subentry.data), catalog, keep_last)
        for subentry_id, subentry in entry.subentries.items()
        if subentry.subentry_type == SUBENTRY_PROBE
    }
    ambients = {
        subentry_id: Ambient(hass, store, subentry_id, dict(subentry.data))
        for subentry_id, subentry in entry.subentries.items()
        if subentry.subentry_type == SUBENTRY_AMBIENT
    }
    store.forget(set(probes) | set(ambients))
    entry.runtime_data = SousChefData(store, catalog, probes, ambients)
    for followed in [*probes.values(), *ambients.values()]:
        followed.async_start()
        entry.async_on_unload(followed.async_stop)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # A subentry added, changed or removed, or the options changed, sets the entry up again
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SousChefConfigEntry) -> bool:
    await entry.runtime_data.store.async_flush()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: SousChefConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
