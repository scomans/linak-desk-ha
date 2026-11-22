"""Drive the desk with the integration's client: height | move CM | stop."""

import asyncio
import logging
import sys

from bleak import BleakScanner

from common import TEST_MAX_CM, load_desk, parser

desk = load_desk()


async def main(address: str, cmd: str, arg: float | None, verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    if cmd == "move" and (arg is None or arg > TEST_MAX_CM):
        sys.exit(f"refusing: move needs a target of at most {TEST_MAX_CM} cm")
    dev = await BleakScanner.find_device_by_address(address, timeout=15)
    d = desk.LinakDesk(lambda: dev, idle_timeout=0, max_cm=TEST_MAX_CM)
    d.add_listener(lambda: print(f"  height={d.height_cm} speed={d.speed}") if d.speed else None)
    try:
        if cmd == "height":
            print("height", await d.refresh())
        elif cmd == "move":
            print("final", await d.move_to(arg))
        elif cmd == "stop":
            await d.stop()
    finally:
        await d.disconnect()


p = parser(__doc__)
p.add_argument("command", choices=["height", "move", "stop"])
p.add_argument("target", nargs="?", type=float, help="target height in cm (move)")
p.add_argument("-v", "--verbose", action="store_true")
a = p.parse_args()
asyncio.run(main(a.address, a.command, a.target, a.verbose))
