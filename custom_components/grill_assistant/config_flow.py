"""Set up a grill, and add its probes."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    BooleanSelector,
    DeviceSelector,
    DeviceSelectorConfig,
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    COLORS,
    CONF_AUTO_ON,
    CONF_CHANNELS,
    CONF_COLORS,
    CONF_DEVICE,
    CONF_GRILL_SENSORS,
    CONF_KEEP_LAST,
    CONF_READING,
    DOMAIN,
    SUBENTRY_PROBE,
)
from .profiles import known_layout, temperature_sensors

TEMPERATURE_SENSORS = EntitySelector(EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=True))
COLOR_SELECTOR = SelectSelector(
    SelectSelectorConfig(options=COLORS, multiple=True, translation_key="color", mode=SelectSelectorMode.DROPDOWN)
)


def _grill_options_schema() -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_GRILL_SENSORS, default=[]): TEMPERATURE_SENSORS,
        vol.Required(CONF_KEEP_LAST, default=True): BooleanSelector(),
    })


class GrillConfigFlow(ConfigFlow, domain=DOMAIN):
    """A grill: a name and its own sensors, then probes added to it."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GrillOptionsFlow:
        return GrillOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_PROBE: ProbeSubentryFlow}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={},
                options={CONF_GRILL_SENSORS: user_input.get(CONF_GRILL_SENSORS, []), CONF_KEEP_LAST: True},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default="Grill"): str,
                vol.Optional(CONF_GRILL_SENSORS, default=[]): TEMPERATURE_SENSORS,
            }),
        )


class GrillOptionsFlow(OptionsFlow):
    """The grill's sensors, and whether a new cook keeps the last one's settings."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(_grill_options_schema(), self.config_entry.options),
        )


def _device_name(hass: HomeAssistant, device_id: str) -> str:
    device = dr.async_get(hass).async_get(device_id)
    return (device.name_by_user or device.name or device_id) if device else device_id


def _sensors_schema(sensors: list[str], with_auto_on: bool) -> vol.Schema:
    """The reading and the sensors of a device with several temperature sensors."""
    fields: dict[Any, Any] = {
        vol.Required(CONF_READING): EntitySelector(EntitySelectorConfig(include_entities=sensors)),
        vol.Optional(CONF_CHANNELS, default=[]): EntitySelector(
            EntitySelectorConfig(include_entities=sensors, multiple=True, reorder=True)
        ),
    }
    if with_auto_on:
        fields[vol.Required(CONF_AUTO_ON, default=False)] = BooleanSelector()
    return vol.Schema(fields)


class ProbeSubentryFlow(ConfigSubentryFlow):
    """A probe: its device and colors. Its sensors are found on the device."""

    def __init__(self) -> None:
        self._device: str | None = None
        self._colors: list[str] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            device = user_input[CONF_DEVICE]
            colors = list(user_input.get(CONF_COLORS) or [])
            taken = {s.data.get(CONF_DEVICE) for s in self._get_entry().subentries.values()}
            sensors = temperature_sensors(self.hass, device)
            if device in taken:
                errors[CONF_DEVICE] = "already_added"
            elif layout := known_layout(self.hass, device):
                return self._create(device, colors, layout.reading, layout.channels, auto_on=True)
            elif len(sensors) == 1:
                return self._create(device, colors, sensors[0], [], auto_on=False)
            elif not sensors:
                errors[CONF_DEVICE] = "no_temperature"
            else:
                self._device, self._colors = device, colors
                return await self.async_step_sensors()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE): DeviceSelector(
                    DeviceSelectorConfig(entity=[EntityFilterSelectorConfig(domain="sensor", device_class="temperature")])
                ),
                vol.Optional(CONF_COLORS, default=[]): COLOR_SELECTOR,
            }),
            errors=errors,
        )

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """A device with several temperature sensors: which is the reading, and their order."""
        assert self._device is not None
        if user_input is not None:
            return self._create(
                self._device,
                self._colors,
                user_input[CONF_READING],
                [c for c in user_input.get(CONF_CHANNELS, []) if c != user_input[CONF_READING]],
                auto_on=user_input[CONF_AUTO_ON],
            )
        return self.async_show_form(
            step_id="sensors",
            data_schema=_sensors_schema(temperature_sensors(self.hass, self._device), with_auto_on=True),
            description_placeholders={"device": _device_name(self.hass, self._device)},
        )

    def _create(self, device: str, colors: list[str], reading: str, channels: list[str], auto_on: bool) -> SubentryFlowResult:
        return self.async_create_entry(
            title=_device_name(self.hass, device),
            data={
                CONF_DEVICE: device,
                CONF_READING: reading,
                CONF_CHANNELS: channels,
                CONF_COLORS: colors,
                CONF_AUTO_ON: auto_on,
            },
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        subentry = self._get_reconfigure_subentry()
        data = dict(subentry.data)
        device = data[CONF_DEVICE]
        sensors = temperature_sensors(self.hass, device)
        # The reading and order of a known probe, or of a single sensor, are not asked
        choose_sensors = known_layout(self.hass, device) is None and len(sensors) > 1
        if user_input is not None:
            data[CONF_COLORS] = list(user_input.get(CONF_COLORS) or [])
            data[CONF_AUTO_ON] = user_input[CONF_AUTO_ON]
            if choose_sensors:
                data[CONF_READING] = user_input[CONF_READING]
                data[CONF_CHANNELS] = [c for c in user_input.get(CONF_CHANNELS, []) if c != data[CONF_READING]]
            return self.async_update_and_abort(self._get_entry(), subentry, data=data)
        schema = vol.Schema({
            vol.Optional(CONF_COLORS, default=[]): COLOR_SELECTOR,
            vol.Required(CONF_AUTO_ON, default=False): BooleanSelector(),
        })
        if choose_sensors:
            schema = schema.extend(_sensors_schema(sensors, with_auto_on=False).schema)
        return self.async_show_form(
            step_id="reconfigure", data_schema=self.add_suggested_values_to_schema(schema, data)
        )
