# Linak DPG1C BLE protocol notes

Notes on the Bluetooth Low Energy interface of the Linak DPG1C controller used in the **IKEA IDÅSEN** desk, as used by this
integration. They come from experiments with one desk (see [`tools/`](../tools/README.md)) and from public notes of other
projects, not from Linak documentation.

## Contents

- [Discovery and connection](#discovery-and-connection)
- [GATT layout](#gatt-layout)
- [Height and speed](#height-and-speed)
- [Commands](#commands)
- [Moving to a height](#moving-to-a-height)
- [Open questions](#open-questions)

## Discovery and connection

| Item | Value |
|---|---|
| Advertised service UUID | `99fa0001-338a-1024-8a49-009c0215f78a` |
| Advertising | only while no central is connected |
| Pairing | required: the controller drops unbonded centrals after a short time, so the integration bonds on first connect |
| Connections | **one** at a time: disconnect the phone app before using the integration |

Because the desk stops advertising while someone is connected, a connection held forever that silently drops makes the
desk unreachable. The integration therefore connects on demand and disconnects after an idle time.

## GATT layout

All custom UUIDs share the base `99faxxxx-338a-1024-8a49-009c0215f78a`.

| Characteristic | Properties | Purpose |
|---|---|---|
| `99fa0002` | write | **Command**: up, down, stop, wake-up |
| `99fa0021` | read, notify | **Height and speed** |
| `99fa0029`, `99fa002a` | read | Unknown, probably limits (see `tools/read_limits.py`) |
| `99fa0031` | write | **Reference input** (target height), ignored by this controller apart from the stop value |

## Height and speed

The height characteristic holds 4 bytes, little endian: `uint16 height, int16 speed`.

- `height` is in 0.1 mm above the lowest position. On the IDÅSEN raw `0` is **62.0 cm**, so `cm = 62 + raw / 100`.
- `speed` is signed (negative while moving down), unit about 0.01 mm/s.
- Notifications arrive while the desk moves; the integration subscribes on connect and reads the value once.

The usable range on the IDÅSEN is about 62 to 127 cm.

## Commands

All values are `uint16`, little endian, written without response.

| Value | Bytes | Characteristic | Meaning |
|---|---|---|---|
| 71 | `47 00` | command | move up (for a short time, repeat to keep moving) |
| 70 | `46 00` | command | move down (for a short time, repeat to keep moving) |
| 255 | `ff 00` | command | stop |
| 254 | `fe 00` | command | wake up, sent before a move |
| 32769 | `01 80` | reference input | stop |

## Moving to a height

Writing a target height to the reference input did not move this desk (`tools/move_experiment.py`). The integration
therefore:

1. sends wake-up, then repeats up or down every 200 ms while watching the height notifications,
2. sends stop early to allow for coasting: about 0.8 cm at full speed, estimated as `max(0.2 cm, |speed| / 1000 * 0.13)`,
3. waits 1.5 s for the desk to settle and corrects up to twice if it is more than 0.5 cm off,
4. reconnects and retries (up to three attempts) if the connection drops during the move.

## Open questions

- Meaning and format of `99fa0029` and `99fa002a`.
- Whether other DPG1C desks (not IDÅSEN) use a different base height.
- Whether the reference input works on other controller firmware versions.
