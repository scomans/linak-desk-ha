"""Print services and characteristics of the desk and the current height."""

import asyncio

from bleak import BleakClient

from common import HEIGHT, parse_height, parser


async def main(address: str) -> None:
    async with BleakClient(address, timeout=20) as c:
        print("connected, mtu", c.mtu_size)
        for s in c.services:
            print("SVC", s.uuid)
            for ch in s.characteristics:
                print("   ", ch.uuid, ch.properties)
        raw = await c.read_gatt_char(HEIGHT)
        cm, speed = parse_height(raw)
        print(f"height raw {raw.hex()} => {cm:.1f} cm, speed {speed}")


asyncio.run(main(parser(__doc__).parse_args().address))
