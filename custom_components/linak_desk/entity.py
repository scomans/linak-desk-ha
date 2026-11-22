from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .desk import LinakDesk


class LinakEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, desk: LinakDesk, address: str, name: str) -> None:
        self._desk = desk
        self._address = address
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={("bluetooth", address)},
            name=name,
            manufacturer="Linak / IKEA",
            model="IDÅSEN (DPG1C)",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._desk.add_listener(self._changed))

    def _changed(self) -> None:
        self.async_write_ha_state()
