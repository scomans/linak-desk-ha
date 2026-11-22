# Linak Desk (IKEA IDÅSEN) for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/scomans/linak-desk-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/scomans/linak-desk-ha/actions/workflows/validate.yml)
[![Tests](https://github.com/scomans/linak-desk-ha/actions/workflows/tests.yml/badge.svg)](https://github.com/scomans/linak-desk-ha/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Unofficial Home Assistant integration for standing desks with a **Linak DPG1C** controller, such as the **IKEA IDÅSEN**.
It runs completely locally over Bluetooth, no cloud and no account needed.

See [docs/protocol.md](docs/protocol.md) for the Bluetooth protocol as far as it is known.

> **Unofficial.** This project is not affiliated with, endorsed by or supported by Linak or IKEA.
> Brand names and logos belong to their owners.

## Features

- Current desk height, restored after a restart
- Buttons to move to a sitting or standing height, and to stop
- Sitting and standing heights adjustable as entities or in the options
- Connects only when needed and disconnects after an idle time, so the desk stays reachable for other clients

## Requirements

- Home Assistant 2024.11 or newer
- The [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/) with a working adapter or an
  [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html) within range of the desk

## Installation

### HACS (custom repository)

[![Open your Home Assistant instance and open this repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=scomans&repository=linak-desk-ha&category=integration)

Use the button above, or add the repository by hand:

1. In HACS open the three-dot menu, choose **Custom repositories** and add
   `https://github.com/scomans/linak-desk-ha` as category **Integration**.
2. Install **Linak Desk (IKEA IDÅSEN)** and restart Home Assistant.

### Manual

1. Copy the folder `custom_components/linak_desk` of this repository to `<config>/custom_components/linak_desk`.
2. Restart Home Assistant.

## Setup

1. Disconnect the phone app (the controller accepts only **one** Bluetooth connection at a time).
2. The desk is discovered automatically. Otherwise go to **Settings > Devices & services > Add integration >
   Linak Desk** and pick it from the list.
3. On the first connection the integration bonds with the desk. If the desk asks for it, press its pairing button.

### Options

**Settings > Devices & services > Linak Desk > Configure**

| Option | Default | Description |
|---|---|---|
| Sitting height (cm) | 72 | Target of the **Sit** button. |
| Standing height (cm) | 110 | Target of the **Stand** button. |
| Disconnect after idle (seconds) | 20 | After this many seconds without a command the integration disconnects. 0 keeps the connection. |

## Entities

| Entity | Type | Description |
|---|---|---|
| Height | sensor, cm | Current height. Read every 15 minutes, when the desk is seen again, and live while it moves. |
| Sit | button | Moves to the sitting height. |
| Stand | button | Moves to the standing height. |
| Stop | button | Stops a running move. |
| Sitting height | number (config) | Sitting height, same value as in the options. |
| Standing height | number (config) | Standing height, same value as in the options. |

## How it works

- **Connecting.** The desk only advertises while nobody is connected. The integration connects on demand (button press,
  periodic read, or when the desk shows up again) and disconnects after the idle time.
- **Moving.** The controller ignores a target height, so the integration repeats up or down commands, stops early to allow
  for coasting and corrects up to twice. A dropped connection during a move is retried.

## Limitations

- Height changes made with the desk's own buttons are only seen at the next read (at most 15 minutes later, or when
  the desk advertises again).
- Only tested with one IKEA IDÅSEN. Other DPG1C desks may use a different base height.

## Troubleshooting

- Disconnect the phone app and other Bluetooth clients.
- Check **Settings > Devices & services > Bluetooth > Advertisement monitor** (Advanced) to see whether Home Assistant
  sees the desk at all. If not, it is an adapter or range issue.
- Enable debug logging and look for lines with `custom_components.linak_desk`:

```yaml
logger:
  logs:
    custom_components.linak_desk: debug
```

## Development

```bash
pip install -r tests/requirements.txt
python -m unittest discover -s tests -v
```

The tests cover the Home Assistant independent client in `desk.py`; Home Assistant itself is not needed. Scripts for exploring
the desk and for driving it without Home Assistant are in [tools/](tools/README.md).

## AI disclosure

This project was developed with the help of an AI coding assistant ([Claude Code](https://claude.com/claude-code) by Anthropic).
Large parts of the code, the tests, the tools and the documentation were written or drafted with it, together with a human
who ran the experiments on a real desk and uses the integration.

AI-written code can contain mistakes and the protocol notes are inferences, not manufacturer documentation. Please review the
code before you rely on it, and report anything that looks wrong.

## License

[MIT](LICENSE)
