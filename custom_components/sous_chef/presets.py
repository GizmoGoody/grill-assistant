"""Where presets come from: published charts, and foods the user adds.

A source is one published chart. Each gives a doneness level, as a
temperature, for the foods it covers. Foods share one list of names and icons
across every source, so switching source keeps the food when the new source
has it. Each value is copied from its chart in the units the chart gives. A
chart that gives only one unit has the other converted and rounded as the
other charts round it.

A chart that gives a range (ThermoWorks) is given here by the low end of the
range: the temperature at which the food reaches that doneness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.const import UnitOfTemperature
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import CONF_ICON, CONF_LEVELS, CONF_NAME, CONF_TEMPERATURE, CONF_UNIT

CUSTOM = "custom"
OTHER = "other"
MINE = "mine"
DEFAULT_ICON = "mdi:food"


@dataclass(frozen=True)
class Level:
    """A doneness level: its temperature in °F and in °C."""

    f: float
    c: float
    # A safe minimum the chart says to rest at for this long after cooking
    rest_minutes: int | None = None
    # A core temperature the chart says to hold for this long
    hold_minutes: int | None = None

    def in_unit(self, unit: str) -> float:
        if unit == UnitOfTemperature.FAHRENHEIT:
            return self.f
        if unit == UnitOfTemperature.CELSIUS:
            return self.c
        return round(TemperatureConverter.convert(self.c, UnitOfTemperature.CELSIUS, unit), 1)

    @classmethod
    def of(cls, temperature: float, unit: str) -> Level:
        """A level given in one unit."""
        f = TemperatureConverter.convert(temperature, unit, UnitOfTemperature.FAHRENHEIT)
        c = TemperatureConverter.convert(temperature, unit, UnitOfTemperature.CELSIUS)
        return cls(f=round(f, 1), c=round(c, 1))


@dataclass(frozen=True)
class Source:
    """One published chart, or the user's own foods."""

    key: str
    url: str | None
    # The countries a government chart is for. Empty: any country.
    countries: tuple[str, ...]
    government: bool
    foods: dict[str, dict[str, Level]]


# Every source's foods, in the order the Food type select lists them
FOODS = [
    "beef",
    "ground_meat",
    "pork",
    "ham",
    "bbq",
    "poultry",
    "game",
    "fish",
    "shellfish",
    "eggs",
    "leftovers",
]

SOURCES = [
    Source(
        key="foodsafety_gov",
        url="https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures",
        countries=("US",),
        government=True,
        foods={
            "beef": {"safe_minimum": Level(145, 63, rest_minutes=3)},
            "ground_meat": {"safe_minimum": Level(160, 71)},
            "pork": {"safe_minimum": Level(145, 63, rest_minutes=3)},
            "poultry": {"safe_minimum": Level(165, 74)},
            "fish": {"safe_minimum": Level(145, 63)},
        },
    ),
    Source(
        key="health_canada",
        url="https://www.canada.ca/en/health-canada/services/general-food-safety-tips/safe-internal-cooking-temperatures.html",
        countries=("CA",),
        government=True,
        foods={
            "beef": {
                "medium_rare": Level(145, 63),
                "medium": Level(160, 71),
                "well_done": Level(170, 77),
            },
            "ground_meat": {"safe_minimum": Level(160, 71)},
            "pork": {"safe_minimum": Level(160, 71)},
            "poultry": {"pieces": Level(165, 74), "whole": Level(180, 82)},
            "game": {"safe_minimum": Level(165, 74)},
            "fish": {"safe_minimum": Level(158, 70)},
            "shellfish": {"safe_minimum": Level(165, 74)},
            "eggs": {"safe_minimum": Level(165, 74)},
            "leftovers": {"safe_minimum": Level(165, 74)},
        },
    ),
    Source(
        key="uk_fsa",
        url="https://www.gov.uk/government/publications/cooking-your-food/cooking-your-food",
        countries=("GB",),
        government=True,
        foods={
            "ground_meat": {"cooked_through": Level(158, 70, hold_minutes=2)},
            "pork": {"cooked_through": Level(158, 70, hold_minutes=2)},
            "poultry": {"cooked_through": Level(158, 70, hold_minutes=2)},
        },
    ),
    Source(
        key="fsanz",
        url="https://www.foodstandards.gov.au/consumer/prevention-of-foodborne-illness/food-safety-basics",
        countries=("AU", "NZ"),
        government=True,
        foods={
            "ground_meat": {"safe_minimum": Level(167, 75)},
            "poultry": {"safe_minimum": Level(167, 75)},
        },
    ),
    Source(
        key="thermoworks",
        url="https://www.thermoworks.com/blogs/thermoblog/chef-recommended-tw-approved",
        countries=(),
        government=False,
        foods={
            "beef": {
                "rare": Level(120, 49),
                "medium_rare": Level(130, 54),
                "medium": Level(135, 57),
                "medium_well": Level(145, 63),
                "well_done": Level(155, 68),
            },
            "ground_meat": {"safe_minimum": Level(160, 71)},
            "pork": {"usda_done": Level(145, 63), "well_done": Level(150, 66)},
            "ham": {"raw": Level(160, 71), "precooked": Level(140, 60)},
            "bbq": {"done": Level(190, 88)},
            "poultry": {"safe_minimum": Level(165, 74), "dark_meat": Level(175, 79)},
            "fish": {"tuna_swordfish_marlin": Level(125, 52), "other_fish": Level(140, 60)},
            "eggs": {"safe_minimum": Level(160, 71)},
            "leftovers": {"safe_minimum": Level(165, 74)},
        },
    ),
]


@dataclass
class Catalog:
    """The sources in the order the Source select lists them, with the user's foods last.

    Government charts for Home Assistant's country come first, so the first of
    them is a new probe's source. Brand charts follow, then the other
    countries' charts.
    """

    sources: dict[str, Source]
    icons: dict[str, str] = field(default_factory=dict)

    @classmethod
    def build(cls, country: str | None, foods: list[dict[str, Any]]) -> Catalog:
        home = [s for s in SOURCES if s.government and country in s.countries]
        brands = [s for s in SOURCES if not s.government]
        abroad = [s for s in SOURCES if s.government and country not in s.countries]
        mine = Source(
            key=MINE,
            url=None,
            countries=(),
            government=False,
            foods={
                food[CONF_NAME]: {
                    level[CONF_NAME]: Level.of(level[CONF_TEMPERATURE], food[CONF_UNIT])
                    for level in food.get(CONF_LEVELS, [])
                }
                for food in foods
            },
        )
        return cls(
            sources={s.key: s for s in [*home, *brands, *abroad, mine]},
            icons={food[CONF_NAME]: food.get(CONF_ICON) or DEFAULT_ICON for food in foods},
        )

    @property
    def default_source(self) -> str:
        return next(iter(self.sources))

    def foods(self, source: str) -> list[str]:
        """A source's foods, then Other for any target."""
        foods = self.sources[source].foods
        return [*(f for f in FOODS if f in foods), *(f for f in foods if f not in FOODS), OTHER]

    def levels(self, source: str, food: str) -> dict[str, Level]:
        return self.sources[source].foods.get(food, {})

    def url(self, source: str) -> str | None:
        return self.sources[source].url
