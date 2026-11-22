"""Check idle disconnect and reconnect: read, wait, then move to 115 cm."""

import asyncio
import logging
import time

from bleak import BleakScanner

from common import TEST_MAX_CM, load_desk, parser

desk = load_desk()


async def main(address: str) -> None:
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(message)s")
    logging.getLogger("bleak").setLevel(logging.WARNING)
    dev = await BleakScanner.find_device_by_address(address, timeout=15)
    d = desk.LinakDesk(lambda: dev, idle_timeout=5, max_cm=TEST_MAX_CM)
    print("t0 refresh:", await d.refresh(), "connected:", d.connected)
    await asyncio.sleep(8)
    print("after idle: connected =", d.connected)
    print("waiting 150 s ...")
    await asyncio.sleep(150)
    t = time.time()
    print("move 115.0 ->", await d.move_to(115.0), f"({time.time() - t:.1f} s incl. reconnect)")
    await asyncio.sleep(8)
    print("final connected =", d.connected)


asyncio.run(main(parser(__doc__).parse_args().address))
