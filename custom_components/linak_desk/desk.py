"""BLE client for Linak DPG1C desk controllers (IKEA IDÅSEN).

No Home Assistant imports, so it can be driven from a CLI as well.

Design: connect on demand, keep the link only while it is useful and
disconnect after ``idle_timeout`` seconds. The controller accepts a single
BLE connection, so holding it forever (and failing to notice that it silently
dropped) is what makes naive integrations stop working after a few minutes.
Every public call re-establishes the connection if needed.
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from collections.abc import Callable

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakNotFoundError,
    establish_connection,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_UUID = "99fa0001-338a-1024-8a49-009c0215f78a"
UUID_HEIGHT = "99fa0021-338a-1024-8a49-009c0215f78a"  # read/notify: <Hh> height, speed
UUID_COMMAND = "99fa0002-338a-1024-8a49-009c0215f78a"  # write: up/down/stop/wakeup
UUID_REFERENCE_INPUT = "99fa0031-338a-1024-8a49-009c0215f78a"  # write: target height

CMD_UP = struct.pack("<H", 71)
CMD_DOWN = struct.pack("<H", 70)
CMD_STOP = struct.pack("<H", 255)
CMD_WAKEUP = struct.pack("<H", 254)
REF_STOP = struct.pack("<H", 32769)

BASE_HEIGHT_CM = 62.0  # raw 0 == 62 cm on the IDÅSEN
MIN_HEIGHT_CM = 62.0
MAX_HEIGHT_CM = 127.0
TOLERANCE_CM = 0.5
COAST_MIN_CM = 0.2
COAST_S = 0.13  # measured: ~0.8 cm braking distance at full speed (speed unit 0.01 mm/s)


class DeskError(Exception):
    """Base error."""


class DeskNotFound(DeskError):
    """Desk is not visible to any Bluetooth adapter."""


def raw_to_cm(raw: int) -> float:
    return BASE_HEIGHT_CM + raw / 100


def cm_to_raw(cm: float) -> int:
    return round((cm - BASE_HEIGHT_CM) * 100)


class LinakDesk:
    def __init__(
        self,
        device_provider: Callable[[], BLEDevice | None],
        name: str = "desk",
        idle_timeout: float = 30.0,
        min_cm: float = MIN_HEIGHT_CM,
        max_cm: float = MAX_HEIGHT_CM,
    ) -> None:
        self._device_provider = device_provider
        self._name = name
        self._idle_timeout = idle_timeout
        self.min_cm = min_cm
        self.max_cm = max_cm
        self._client: BleakClient | None = None
        self._conn_lock = asyncio.Lock()
        self._move_lock = asyncio.Lock()
        self._stop_requested = asyncio.Event()
        self._height_event = asyncio.Event()
        self._idle_handle: asyncio.TimerHandle | None = None
        self._busy = 0
        self._listeners: list[Callable[[], None]] = []
        self.height_cm: float | None = None
        self.speed: int = 0
        self.connected = False

    # -- listeners --------------------------------------------------------
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    def _notify_listeners(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("listener failed")

    # -- connection -------------------------------------------------------
    def _on_disconnect(self, _client: BleakClient) -> None:
        _LOGGER.debug("%s: disconnected", self._name)
        self._client = None
        self.connected = False
        self._height_event.set()  # wake up a running move so it can retry
        self._notify_listeners()

    def _on_height(self, _char, data: bytearray) -> None:
        if len(data) < 4:
            return
        raw, speed = struct.unpack("<Hh", bytes(data[:4]))
        self.height_cm = round(raw_to_cm(raw), 1)
        self.speed = speed
        self._height_event.set()
        self._notify_listeners()

    async def _ensure_connected(self) -> BleakClient:
        async with self._conn_lock:
            if self._client is not None and self._client.is_connected:
                return self._client
            device = self._device_provider()
            if device is None:
                raise DeskNotFound(f"{self._name} not in range of any adapter")
            _LOGGER.debug("%s: connecting", self._name)
            try:
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    self._name,
                    disconnected_callback=self._on_disconnect,
                    max_attempts=4,
                    ble_device_callback=self._device_provider,
                    # The controller drops unbonded centrals; bond on first connect
                    # (no-op once bonded).
                    pair=True,
                )
            except BleakNotFoundError as err:
                raise DeskNotFound(str(err)) from err
            try:
                await client.start_notify(UUID_HEIGHT, self._on_height)
                self._on_height(None, await client.read_gatt_char(UUID_HEIGHT))
            except Exception:
                await client.disconnect()
                raise
            self._client = client
            self.connected = True
            self._notify_listeners()
            return client

    async def disconnect(self) -> None:
        self._cancel_idle()
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            try:
                await client.disconnect()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("disconnect failed", exc_info=True)
        self.connected = False
        self._notify_listeners()

    def _cancel_idle(self) -> None:
        if self._idle_handle is not None:
            self._idle_handle.cancel()
            self._idle_handle = None

    def _arm_idle(self) -> None:
        self._cancel_idle()
        if self._idle_timeout <= 0 or self._busy:
            return
        loop = asyncio.get_running_loop()
        self._idle_handle = loop.call_later(
            self._idle_timeout, lambda: loop.create_task(self.disconnect())
        )

    # -- public API -------------------------------------------------------
    async def refresh(self) -> float | None:
        """Connect, read the current height, disconnect after idle timeout."""
        self._busy += 1
        self._cancel_idle()
        try:
            await self._ensure_connected()
            return self.height_cm
        finally:
            self._busy -= 1
            self._arm_idle()

    async def stop(self) -> None:
        self._stop_requested.set()
        self._busy += 1
        try:
            client = await self._ensure_connected()
            await client.write_gatt_char(UUID_COMMAND, CMD_STOP, response=False)
            await client.write_gatt_char(UUID_REFERENCE_INPUT, REF_STOP, response=False)
        finally:
            self._busy -= 1
            self._arm_idle()

    async def move_to(self, target_cm: float, timeout: float = 90.0) -> float | None:
        """Drive to ``target_cm``. Retries over dropped connections."""
        target_cm = max(self.min_cm, min(self.max_cm, target_cm))
        target_raw = cm_to_raw(target_cm)
        self._stop_requested.set()  # abort a move that is still running
        async with self._move_lock:
            self._stop_requested.clear()
            self._busy += 1
            self._cancel_idle()
            deadline = time.monotonic() + timeout
            last_err: Exception | None = None
            try:
                for attempt in range(1, 4):
                    try:
                        for _ in range(3):  # main run + up to two corrections
                            await self._drive(target_cm, target_raw, deadline)
                            if (
                                self._stop_requested.is_set()
                                or abs(self.height_cm - target_cm) <= TOLERANCE_CM
                            ):
                                break
                        return self.height_cm
                    except (DeskNotFound, OSError, asyncio.TimeoutError, EOFError) as err:
                        last_err = err
                        _LOGGER.debug("move attempt %d failed: %r", attempt, err)
                        await asyncio.sleep(1)
                    except Exception as err:  # bleak errors
                        last_err = err
                        _LOGGER.debug("move attempt %d failed: %r", attempt, err)
                        await asyncio.sleep(1)
                    if time.monotonic() > deadline:
                        break
                raise DeskError(f"move to {target_cm} cm failed: {last_err!r}")
            finally:
                self._busy -= 1
                self._arm_idle()

    async def _drive(self, target_cm: float, target_raw: int, deadline: float) -> None:
        """Move with repeated UP/DOWN commands (the reference-input register
        is ignored by this controller). Stops early to allow for coasting."""
        client = await self._ensure_connected()
        if self.height_cm is None:
            raise DeskError("height unknown")
        up = target_cm > self.height_cm
        if abs(target_cm - self.height_cm) <= TOLERANCE_CM:
            return
        cmd = CMD_UP if up else CMD_DOWN
        await client.write_gatt_char(UUID_COMMAND, CMD_WAKEUP, response=False)
        try:
            while True:
                if self._stop_requested.is_set():
                    break
                if client is not self._client or not client.is_connected:
                    raise DeskNotFound("connection lost while moving")
                if time.monotonic() > deadline:
                    raise asyncio.TimeoutError("move timed out")
                remaining = (target_cm - self.height_cm) if up else (self.height_cm - target_cm)
                coast = max(COAST_MIN_CM, abs(self.speed) / 1000 * COAST_S)
                if remaining <= coast:
                    _LOGGER.debug("stop issued at %.1f cm, speed %d, coast %.2f", self.height_cm, self.speed, coast)
                    break
                await client.write_gatt_char(UUID_COMMAND, cmd, response=False)
                await asyncio.sleep(0.2)
        finally:
            if client.is_connected:
                try:
                    await client.write_gatt_char(UUID_COMMAND, CMD_STOP, response=False)
                except Exception:  # noqa: BLE001
                    _LOGGER.debug("stop write failed", exc_info=True)
        # let it settle, then final correction is left to the caller
        await asyncio.sleep(1.5)
        _LOGGER.debug("settled at %.1f cm (target %.1f)", self.height_cm, target_cm)
