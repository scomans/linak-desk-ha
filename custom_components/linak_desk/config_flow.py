from __future__ import annotations

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import (
    CONF_IDLE_TIMEOUT,
    CONF_SIT_CM,
    CONF_STAND_CM,
    DEFAULT_IDLE_TIMEOUT,
    DEFAULT_SIT_CM,
    DEFAULT_STAND_CM,
    DOMAIN,
)
from .desk import MAX_HEIGHT_CM, MIN_HEIGHT_CM, SERVICE_UUID

HEIGHT = vol.All(vol.Coerce(float), vol.Range(min=MIN_HEIGHT_CM, max=MAX_HEIGHT_CM))


class LinakDeskConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._found: dict[str, BluetoothServiceInfoBleak] = {}

    @staticmethod
    def async_get_options_flow(config_entry):
        return LinakDeskOptionsFlow()

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None) -> ConfigFlowResult:
        assert self._discovery
        if user_input is not None:
            return self._create(self._discovery)
        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm", description_placeholders={"name": self._discovery.name}
        )

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            info = self._found[user_input[CONF_ADDRESS]]
            await self.async_set_unique_id(info.address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self._create(info)
        current = self._async_current_ids()
        self._found = {
            i.address: i
            for i in async_discovered_service_info(self.hass, connectable=True)
            if SERVICE_UUID in i.service_uuids and i.address not in current
        }
        if not self._found:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In({a: f"{i.name} ({a})" for a, i in self._found.items()})}
            ),
        )

    def _create(self, info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        return self.async_create_entry(
            title=info.name, data={CONF_ADDRESS: info.address, CONF_NAME: info.name}
        )


class LinakDeskOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        o = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SIT_CM, default=o.get(CONF_SIT_CM, DEFAULT_SIT_CM)): HEIGHT,
                    vol.Required(CONF_STAND_CM, default=o.get(CONF_STAND_CM, DEFAULT_STAND_CM)): HEIGHT,
                    vol.Required(
                        CONF_IDLE_TIMEOUT, default=o.get(CONF_IDLE_TIMEOUT, DEFAULT_IDLE_TIMEOUT)
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=600)),
                }
            ),
        )
