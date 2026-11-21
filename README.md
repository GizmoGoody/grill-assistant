# Sous Chef

*For the grill, the smoker and the kitchen.*

Sous Chef turns any food thermometer in Home Assistant into a cook. You say what you are cooking and how done you want it, from a chart you trust. It tells you how far along the food is, how fast it is heating, when it will be done, whether it has stalled, and when anything is out of range.

Every cook is kept as entities, so every browser shows the same cook at once, a change made in one shows in all, and automations can use it. It needs no helpers and no automations.

The [Sous Chef Card](https://github.com/GizmoGoody/sous-chef-card) shows it on a dashboard.

> [!WARNING]
> **Alpha developmental software. Use with caution.** Do not rely on it alone for food safety. Check the temperature with a second thermometer before serving.

## Install

1. Go to **Settings → Marketplace**, then ⋮ → **Add from link**. Enter `GizmoGoody/sous-chef`, type **Integration**.
2. Install **Sous Chef**. For a pre-release, use ⋮ → **Install another version**.

## Set up

1. **Settings → Devices & services → Add integration → Sous Chef.** There is one Sous Chef entry. It holds all your probes and ambient sensors.
2. On its page, choose **Add probe**, then choose the probe device and, optionally, its colors (several, in order, for a striped probe). A probe is added once and used anywhere.
   - A **ThermoWorks RFX MEAT** needs nothing else: its internal temperature is channel 0, and its channels 1 to 4 run from the tip.
   - A device with **one** temperature sensor needs nothing else.
   - A device with **several** temperature sensors asks for its internal temperature (one sensor, or empty for the lowest of the channels) and its channels in order from the tip.
3. Choose **Add ambient sensor** for each sensor that reads the air in a grill, pit or oven. It gets alarms, no food and no target.
4. Choose **Add food** for a food no chart lists, such as a brisket, with your own doneness levels. It is listed under the source **Mine**.
5. **Configure** sets whether a new cook keeps the last source, food type, doneness and target (on by default).

## How a cook runs

- A cook runs while the probe's **Active** switch is on. Turn it on whenever you like, even with the probe still on its charger, and set up the cook.
- A probe set to **turn on when it starts reporting** turns itself on, for example when an RFX probe comes off its charger. This is on by default for known probes such as the RFX MEAT.
- The **internal temperature** is the one temperature that stands for the inside of the food. Progress, Rate, Done at, Done, Stalled and the probe's alarm all use it.
- The cook's start is the lowest internal temperature since the probe was turned on. Once the probe is in the food, that is the food's own temperature. Progress runs from that start to the target.
- A lost signal or a restart changes nothing. Turning the probe off ends the cook.
- An RFX probe counts as reporting only while it sends new data. ThermoWorks Cloud keeps showing a probe's last value while it is on its charger, and that old value is treated as no reading.

## Entities

On each probe's own device, beside its temperature sensors. Settings are Configuration entities: they are on the device page and stay out of automatic dashboards.

| Entity | Kind | What it is |
| --- | --- | --- |
| Active | Control | On while the probe is cooking. Turning it on starts a new cook. |
| Source | Configuration | The chart the presets come from. |
| Food type | Configuration | What is cooking: the source's foods, or Other for any target. |
| Doneness | Configuration | The food's levels, or Custom for any other target. Choosing one sets the target. |
| Target | Configuration | The temperature to reach. |
| Pull early by | Configuration | Done turns on this many degrees before the target, for carryover while the food rests. |
| Alarm high, Alarm low | Configuration | The internal temperature must stay below and above these while the probe is on. 0 is no limit. |
| Progress | Sensor | How far the internal temperature has come from the cook's start to the target. |
| Rate | Sensor | Degrees per minute, over a window that adjusts itself: about 2 minutes when the temperature moves fast, up to 15 when it moves slowly. |
| Done at | Sensor | When the internal temperature will reach the target, less Pull early by, at its current rate. |
| Done | Sensor | On once the internal temperature reaches the target, less Pull early by. |
| Stalled | Sensor | On while it rises less than 0.05 °F a minute short of the target. |
| Alarm | Sensor | On while the internal temperature is above Alarm high or below Alarm low. |
| Max | Sensor | The highest of the probe's channels. Only for probes with channels. |

On each ambient sensor's device: **Alarm high** and **Alarm low** (Configuration, 0 is no limit) and **Alarm** (on while the temperature is out of range).

An Alarm low turns on only once the temperature has first reached it, so lighting a grill or putting a probe in cold food raises no alarm.

### Presets

Every preset names its source: one published chart. Government charts give a safe minimum; brand charts give doneness for taste. Government charts for your Home Assistant country come first, and the first of them is a new probe's source. Each value is copied from its chart in the units it gives. Where a chart gives a range, the preset is the low end of the range.

| Source | Country | Chart |
| --- | --- | --- |
| FoodSafety.gov (Safe Minimum Internal Temperatures) | US | [foodsafety.gov](https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures) |
| Health Canada (Safe Cooking Temperatures) | CA | [canada.ca](https://www.canada.ca/en/health-canada/services/general-food-safety-tips/safe-internal-cooking-temperatures.html) |
| UK Food Standards Agency (Cooking Your Food) | GB | [gov.uk](https://www.gov.uk/government/publications/cooking-your-food/cooking-your-food) |
| FSANZ (Food Safety Basics) | AU, NZ | [foodstandards.gov.au](https://www.foodstandards.gov.au/consumer/prevention-of-foodborne-illness/food-safety-basics) |
| ThermoWorks (Chef-Recommended Temps) | any | [thermoworks.com](https://www.thermoworks.com/blogs/thermoblog/chef-recommended-tw-approved) |
| Mine | any | Your own foods, added with **Add food**. |

### For the Sous Chef Card

- The **Progress** sensor's attributes: `internal` (entity ID, or empty for the lowest of the channels), `channels` (entity IDs, from the tip), `colors` (Home Assistant color names, in order) and `start`.
- **Source**, **Food type** and **Doneness** carry the chart's link as `url`. Doneness also carries `rest_minutes` or `hold_minutes` when the chart gives one.
- The ambient **Alarm** sensor's `sensor` attribute is the ambient sensor's entity ID.

## License

MIT. See [LICENSE](LICENSE).
