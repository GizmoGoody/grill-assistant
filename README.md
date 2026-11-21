# Sous Chef

Sous Chef turns any meat thermometer in Home Assistant into a cook. You say what you are cooking and how done you want it. It tells you how far along the meat is, how fast it is heating, when it will be done, and whether it has stalled.

Every cook is kept as entities, so every browser shows the same cook at once, a change made in one shows in all, and automations can use it. It needs no helpers and no automations.

The [Sous Chef Card](https://github.com/GizmoGoody/sous-chef-card) shows it on a dashboard.

> [!WARNING]
> **Alpha developmental software. Use with caution.** Do not rely on it alone for food safety. Check the temperature with a second thermometer before serving.

## Install

1. Go to **Settings → Marketplace**, then ⋮ → **Add from link**. Enter `GizmoGoody/sous-chef`, type **Integration**.
2. Install **Sous Chef**. For a pre-release, use ⋮ → **Install another version**.

## Set up

1. **Settings → Devices & services → Add integration → Sous Chef.** Name the grill, and optionally choose the sensors that read the grill itself (ambient, dome). A grill can have several.
2. On the grill, choose **Add probe**, then choose the probe device and, optionally, its colors (several, in order, for a striped probe).
   - A **ThermoWorks RFX MEAT** needs nothing else: its core (channel 0) is the reading, and its sensors (channels 1 to 4) run from the tip.
   - A device with **one** temperature sensor needs nothing else.
   - A device with **several** temperature sensors asks which one is the reading, and the others in order from the tip.
3. **Configure** on the grill sets its sensors, and whether a new cook keeps the last cook type, doneness and target (on by default).
4. A probe's settings (colors, and whether it turns on by itself) are changed with **Reconfigure** on the probe.

## How a cook runs

- A cook runs while the probe's **Active** switch is on. Turn it on whenever you like, even with the probe still on its charger, and set up the cook.
- A probe set to **turn on when it starts reporting** turns itself on, for example when an RFX probe comes off its charger. This is on by default for known probes such as the RFX MEAT.
- The cook's start is the lowest reading since the probe was turned on. Once the probe is in the meat, that is the meat's own temperature. Progress runs from that start to the target.
- A lost signal or a restart changes nothing. Turning the probe off ends the cook.
- An RFX probe counts as reporting only while it sends new data. ThermoWorks Cloud keeps showing a probe's last value while it is on its charger, and that old value is treated as no reading.

## Entities

On each probe's own device, beside its temperature sensors:

| Entity | What it is |
| --- | --- |
| Active | On while the probe is cooking. Turning it on starts a new cook. |
| Cook type | Beef, Ground beef, Pork, Poultry, Seafood or Manual. |
| Doneness | The cook type's presets, or Custom for any other target. Choosing one sets the target. |
| Target | The temperature to reach. |
| Progress | How far the reading has come from the cook's start to the target. |
| Rate | Degrees per minute, over the last ten minutes. |
| Done at | When the reading will reach the target at its current rate. |
| Done | On once the reading reaches the target. |
| Stalled | On while the reading has stopped rising short of the target. |

On the grill's own device: **Active probes**, the number of probes that are on.

### Presets (°F)

| Cook type | Doneness and target |
| --- | --- |
| Beef | Rare 125, Medium rare 135, Medium 145, Medium well 155, Well done 165 |
| Ground beef | Well done 160 |
| Pork | Medium 145, Well done 160 |
| Poultry | Done 165 |
| Seafood | Tuna 130, Salmon 145, Shrimp 145, Scallops 145, Lobster 145 |
| Manual | Any target you set |

### For the Sous Chef Card

- The **Progress** sensor's attributes: `reading` (entity ID), `channels` (entity IDs, from the tip), `colors` (Home Assistant color names, in order) and `start`.
- The **Active probes** sensor's attributes: `grill_sensors` (entity IDs) and `probes` (each probe's Progress entity ID).

## License

MIT. See [LICENSE](LICENSE).
