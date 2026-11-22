from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME, UnitOfLength

from .entity import LinakEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    addr = entry.data[CONF_ADDRESS]
    async_add_entities([HeightSensor(entry.runtime_data, addr, entry.data.get(CONF_NAME, addr))])


class HeightSensor(LinakEntity, RestoreSensor):
    _attr_translation_key = "height"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, desk, address, name) -> None:
        super().__init__(desk, address, name)
        self._attr_unique_id = f"{address}_height"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Show the last known height after a restart until the desk is read again.
        if self._desk.height_cm is None and (last := await self.async_get_last_sensor_data()):
            if isinstance(last.native_value, (int, float)):
                self._desk.height_cm = float(last.native_value)

    @property
    def native_value(self) -> float | None:
        return self._desk.height_cm
