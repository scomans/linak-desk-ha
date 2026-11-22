# Tools

Small scripts for exploring the desk controller and for testing the integration's client without Home Assistant. They need
Python 3.11+, [`bleak`](https://github.com/hbldh/bleak) and `bleak-retry-connector` (`pip install -r requirements.txt`).
Run them from the repository root and pass the desk's Bluetooth address, for example
`python tools/gatt_dump.py AA:BB:CC:DD:EE:FF`. `scan.py` finds the address.

Disconnect the phone app and disable this integration first: the controller accepts one connection at a time.

| Script | What it does | Moves the desk? |
|---|---|---|
| `scan.py` | Lists BLE advertisements, highlights Linak desks | no |
| `gatt_dump.py` | Prints services, characteristics and the current height | no |
| `read_limits.py` | Reads the undocumented characteristics `99fa0029` / `99fa002a` | no |
| `move_experiment.py` | Compares the reference-input register with repeated DOWN commands | yes, about 1.5 cm down |
| `desk_cli.py` | `height`, `move CM`, `stop` through the integration's `LinakDesk` client | yes |
| `idle_test.py` | Checks idle disconnect and reconnect, then moves to 115 cm | yes |

`common.py` holds the shared UUIDs and helpers. Moves are capped at `TEST_MAX_CM` (116.4 cm) in `common.py`.
