"""Shared constants and helpers for the tools in this folder."""

from __future__ import annotations

import argparse
import importlib.util
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESK_PY = ROOT / "custom_components/linak_desk/desk.py"


def _uuid(short: str) -> str:
    return f"99fa{short}-338a-1024-8a49-009c0215f78a"


SERVICE = _uuid("0001")
COMMAND = _uuid("0002")
HEIGHT = _uuid("0021")
LIMIT_A = _uuid("0029")
LIMIT_B = _uuid("002a")
REFERENCE_INPUT = _uuid("0031")

BASE_HEIGHT_CM = 62.0

# Safety cap for live tests on the owner's desk: never drive above this height.
TEST_MAX_CM = 116.4


def load_desk():
    """Import custom_components/linak_desk/desk.py without Home Assistant."""
    spec = importlib.util.spec_from_file_location("desk", DESK_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_height(raw: bytes) -> tuple[float, int]:
    """Return (height in cm, speed) from a height characteristic value."""
    h, speed = struct.unpack("<Hh", bytes(raw[:4]))
    return BASE_HEIGHT_CM + h / 100, speed


def parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("address", help="Bluetooth address of the desk, e.g. AA:BB:CC:DD:EE:FF")
    return p
