"""Linak desk (IKEA IDÅSEN) integration."""

from __future__ import annotations

from datetime import timedelta
import logging
import time

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_IDLE_TIMEOUT, DEFAULT_IDLE_TIMEOUT, REFRESH_INTERVAL_MIN
from .desk import DeskError, LinakDesk

_LOGGER = logging.getLogger(__name__)
RETRY_AFTER_FAIL_S = 120
PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.NUMBER]

type LinakConfigEntry = ConfigEntry[LinakDesk]


async def async_setup_entry(hass: HomeAssistant, entry: LinakConfigEntry) -> bool:
    address: str = entry.data[CONF_ADDRESS]

    def device_provider():
        return bluetooth.async_ble_device_from_address(hass, address, connectable=True)

    idle_timeout = entry.options.get(CONF_IDLE_TIMEOUT, DEFAULT_IDLE_TIMEOUT)
    desk = LinakDesk(device_provider, name=entry.data.get(CONF_NAME, address), idle_timeout=idle_timeout)
    entry.runtime_data = desk

    state = {"running": False, "last_ok": float("-inf"), "last_fail": float("-inf"), "warned": False}

    async def _refresh(*_) -> None:
        if state["running"]:
            return
        state["running"] = True
        try:
            await desk.refresh()
        except Exception as err:  # noqa: BLE001 - never let polling kill the interval
            state["last_fail"] = time.monotonic()
            # Warn once so the reason is visible without debug logging, then stay quiet.
            log = _LOGGER.debug if state["warned"] else _LOGGER.warning
            info = bluetooth.async_last_service_info(hass, address, connectable=True)
            via = f"via {info.source}, RSSI {info.rssi} dBm" if info else "not seen by any adapter"
            log("%s: reading height failed (%s): %s", entry.title, via, err)
            state["warned"] = True
        else:
            state["last_ok"] = time.monotonic()
            if state["warned"]:
                _LOGGER.info("%s: height read again (%.1f cm)", entry.title, desk.height_cm)
            state["warned"] = False
        finally:
            state["running"] = False

    @callback
    def _advertisement(service_info, change) -> None:
        # The desk only advertises while nobody is connected. Seeing it means we can
        # read now - this covers HA start-up, where the first poll runs before the
        # adapter has seen the desk, and desks that were out of range.
        if desk.connected or state["running"]:
            return
        if time.monotonic() - state["last_fail"] < RETRY_AFTER_FAIL_S:
            return  # don't hammer a proxy that just failed to connect
        if desk.height_cm is not None and time.monotonic() - state["last_ok"] < REFRESH_INTERVAL_MIN * 60:
            return
        entry.async_create_background_task(hass, _refresh(), "linak_desk_adv_refresh")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _options_updated(hass: HomeAssistant, entry: LinakConfigEntry) -> None:
        # Preset heights are read live; only a changed idle timeout needs a reload.
        if entry.options.get(CONF_IDLE_TIMEOUT, DEFAULT_IDLE_TIMEOUT) != idle_timeout:
            await hass.config_entries.async_reload(entry.entry_id)
        else:
            desk._notify_listeners()

    entry.async_on_unload(entry.add_update_listener(_options_updated))
    entry.async_on_unload(
        async_track_time_interval(hass, _refresh, timedelta(minutes=REFRESH_INTERVAL_MIN))
    )
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _advertisement,
            bluetooth.BluetoothCallbackMatcher(address=address, connectable=True),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )
    entry.async_on_unload(desk.disconnect)
    # first reading in the background, desk may be out of range
    entry.async_create_background_task(hass, _refresh(), "linak_desk_initial_refresh")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LinakConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
