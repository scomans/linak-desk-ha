"""Read the two (undocumented) limit characteristics 99fa0029 and 99fa002a."""

import asyncio

from bleak import BleakClient

from common import LIMIT_A, LIMIT_B, parser


async def main(address: str) -> None:
    async with BleakClient(address, timeout=20) as c:
        for uuid in (LIMIT_A, LIMIT_B):
            raw = await c.read_gatt_char(uuid)
            print(uuid[:8], "len", len(raw), raw.hex())


asyncio.run(main(parser(__doc__).parse_args().address))
