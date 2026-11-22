from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import CONF_ADDRESS, CONF_NAME, EntityCategory, UnitOfLength

from .const import CONF_SIT_CM, CONF_STAND_CM, DEFAULT_SIT_CM, DEFAULT_STAND_CM
from .desk import MAX_HEIGHT_CM, MIN_HEIGHT_CM
from .entity import LinakEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    desk, addr = entry.runtime_data, entry.data[CONF_ADDRESS]
    name = entry.data.get(CONF_NAME, addr)
    async_add_entities(
        [
            PresetHeightNumber(entry, desk, addr, name, "sit_height", CONF_SIT_CM, DEFAULT_SIT_CM),
            PresetHeightNumber(entry, desk, addr, name, "stand_height", CONF_STAND_CM, DEFAULT_STAND_CM),
        ]
    )


class PresetHeightNumber(LinakEntity, NumberEntity):
    """Preset height stored in the config entry options (shared with the options flow)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_native_min_value = MIN_HEIGHT_CM
    _attr_native_max_value = MAX_HEIGHT_CM
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, desk, address, name, key, option, default) -> None:
        super().__init__(desk, address, name)
        self._entry = entry
        self._option = option
        self._default = default
        self._attr_translation_key = key
        self._attr_unique_id = f"{address}_{key}"

    @property
    def native_value(self) -> float:
        return self._entry.options.get(self._option, self._default)

    async def async_set_native_value(self, value: float) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry, options={**self._entry.options, self._option: value}
        )
        self.async_write_ha_state()
