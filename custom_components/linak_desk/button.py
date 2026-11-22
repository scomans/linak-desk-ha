import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import CONF_SIT_CM, CONF_STAND_CM, DEFAULT_SIT_CM, DEFAULT_STAND_CM
from .entity import LinakEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    desk, addr = entry.runtime_data, entry.data[CONF_ADDRESS]
    name = entry.data.get(CONF_NAME, addr)
    async_add_entities(
        [
            PresetButton(entry, desk, addr, name, "sit", CONF_SIT_CM, DEFAULT_SIT_CM),
            PresetButton(entry, desk, addr, name, "stand", CONF_STAND_CM, DEFAULT_STAND_CM),
            StopButton(desk, addr, name),
        ]
    )


class PresetButton(LinakEntity, ButtonEntity):
    def __init__(self, entry, desk, address, name, key, option, default) -> None:
        super().__init__(desk, address, name)
        self._entry = entry
        self._option = option
        self._default = default
        self._attr_translation_key = key
        self._attr_unique_id = f"{address}_{key}"

    async def async_press(self) -> None:
        # Run in the background: a move can take a minute and must not block the service call.
        self._entry.async_create_background_task(
            self.hass, self._go(), f"linak_desk_move_{self._attr_translation_key}"
        )

    async def _go(self) -> None:
        height = self._entry.options.get(self._option, self._default)
        try:
            await self._desk.move_to(height)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Moving desk to %.1f cm failed: %s", height, err)


class StopButton(LinakEntity, ButtonEntity):
    _attr_translation_key = "stop"

    def __init__(self, desk, address, name) -> None:
        super().__init__(desk, address, name)
        self._attr_unique_id = f"{address}_stop"

    async def async_press(self) -> None:
        await self._desk.stop()
