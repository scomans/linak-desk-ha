"""List BLE advertisements and highlight Linak desks."""

import asyncio

from bleak import BleakScanner

from common import SERVICE


async def main() -> None:
    found = await BleakScanner.discover(timeout=10, return_adv=True)
    for dev, adv in sorted(found.values(), key=lambda x: -x[1].rssi):
        mark = "DESK" if SERVICE in adv.service_uuids else "    "
        print(f"{mark} {dev.address}  {adv.rssi:4d} dBm  {adv.local_name or ''}")


asyncio.run(main())
