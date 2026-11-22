"""Compare the reference-input register with a repeated DOWN command.

Moves the desk about 1.5 cm down in total.
"""

import asyncio
import struct

from bleak import BleakClient

from common import BASE_HEIGHT_CM, COMMAND, HEIGHT, REFERENCE_INPUT, parse_height, parser


async def height(c: BleakClient) -> float:
    return parse_height(await c.read_gatt_char(HEIGHT))[0]


async def main(address: str) -> None:
    async with BleakClient(address, timeout=20) as c:
        start = await height(c)
        print("start", start)
        # A: wake up + reference input (response=True), target 1.5 cm lower
        target = round((start - 1.5 - BASE_HEIGHT_CM) * 100)
        await c.write_gatt_char(COMMAND, struct.pack("<H", 254), response=True)
        await c.write_gatt_char(REFERENCE_INPUT, struct.pack("<H", target), response=True)
        await asyncio.sleep(2.5)
        print("A reference input:", await height(c))
        # B: DOWN command repeated for about one second
        for _ in range(5):
            await c.write_gatt_char(COMMAND, struct.pack("<H", 70), response=False)
            await asyncio.sleep(0.2)
        await c.write_gatt_char(COMMAND, struct.pack("<H", 255), response=False)
        await asyncio.sleep(1.0)
        print("B down loop:", await height(c))


asyncio.run(main(parser(__doc__).parse_args().address))
