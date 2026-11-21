"""A probe's source, food type and doneness.

Each carries the source's chart link as its url attribute, so the Sous Chef
Card can show where a target comes from.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SousChefConfigEntry
from .entity import ProbeEntity
from .presets import MINE


async def async_setup_entry(
    hass: HomeAssistant, entry: SousChefConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for subentry_id, probe in entry.runtime_data.probes.items():
        subentry = entry.subentries[subentry_id]
        async_add_entities(
            [
                SourceSelect(hass, subentry, probe, "source"),
                FoodTypeSelect(hass, subentry, probe, "food_type"),
                DonenessSelect(hass, subentry, probe, "doneness"),
            ],
            config_subentry_id=subentry_id,
        )


class PresetSelect(ProbeEntity, SelectEntity):
    """A setting of the cook's preset."""

    _attr_entity_category = EntityCategory.CONFIG
    _unrecorded_attributes = frozenset({"url"})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"url": self.probe.catalog.url(self.probe.source)}


class SourceSelect(PresetSelect):
    """The chart the presets come from: government charts for Home Assistant's country first."""

    @property
    def options(self) -> list[str]:
        return list(self.probe.catalog.sources)

    @property
    def current_option(self) -> str:
        return self.probe.source

    async def async_select_option(self, option: str) -> None:
        self.probe.set_source(option)


class FoodTypeSelect(PresetSelect):
    """What is cooking: one of the source's foods, or Other for any target."""

    @property
    def options(self) -> list[str]:
        return self.probe.foods

    @property
    def current_option(self) -> str:
        return self.probe.food

    @property
    def icon(self) -> str | None:
        # A food of the user's own has its own icon; the built-in foods have theirs in icons.json
        if self.probe.source == MINE:
            return self.probe.catalog.icons.get(self.probe.food)
        return None

    async def async_select_option(self, option: str) -> None:
        self.probe.set_food(option)


class DonenessSelect(PresetSelect):
    """How done: one of the food's levels, or Custom for any other target."""

    @property
    def options(self) -> list[str]:
        return self.probe.doneness_options

    @property
    def current_option(self) -> str:
        return self.probe.doneness

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        level = self.probe.level
        attributes = super().extra_state_attributes
        if level and level.rest_minutes:
            attributes["rest_minutes"] = level.rest_minutes
        if level and level.hold_minutes:
            attributes["hold_minutes"] = level.hold_minutes
        return attributes

    async def async_select_option(self, option: str) -> None:
        self.probe.set_doneness(option)
