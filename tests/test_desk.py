"""Unit tests for the Home Assistant independent desk client (desk.py)."""

import importlib.util
import struct
import unittest
from pathlib import Path

_DESK_PY = Path(__file__).parent.parent / "custom_components/linak_desk/desk.py"
_spec = importlib.util.spec_from_file_location("desk", _DESK_PY)
desk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(desk)


class HeightConversionTest(unittest.TestCase):
    def test_raw_to_cm(self):
        self.assertEqual(desk.raw_to_cm(0), 62.0)
        self.assertEqual(desk.raw_to_cm(5439), 116.39)

    def test_cm_to_raw(self):
        self.assertEqual(desk.cm_to_raw(62), 0)
        self.assertEqual(desk.cm_to_raw(116.39), 5439)

    def test_roundtrip(self):
        for raw in (0, 1, 1000, 4800, 6500):
            self.assertEqual(desk.cm_to_raw(desk.raw_to_cm(raw)), raw)


class HeightNotificationTest(unittest.TestCase):
    def setUp(self):
        self.desk = desk.LinakDesk(lambda: None)
        self.calls = 0
        self.desk.add_listener(self._count)

    def _count(self):
        self.calls += 1

    def test_parses_height_and_speed(self):
        self.desk._on_height(None, bytearray(struct.pack("<Hh", 4800, -321)))
        self.assertEqual(self.desk.height_cm, 110.0)
        self.assertEqual(self.desk.speed, -321)
        self.assertEqual(self.calls, 1)

    def test_ignores_short_frames(self):
        self.desk._on_height(None, bytearray(b"\x01\x02"))
        self.assertIsNone(self.desk.height_cm)
        self.assertEqual(self.calls, 0)


class CommandEncodingTest(unittest.TestCase):
    def test_commands(self):
        self.assertEqual(desk.CMD_UP, b"\x47\x00")
        self.assertEqual(desk.CMD_DOWN, b"\x46\x00")
        self.assertEqual(desk.CMD_STOP, b"\xff\x00")
        self.assertEqual(desk.CMD_WAKEUP, b"\xfe\x00")
        self.assertEqual(desk.REF_STOP, b"\x01\x80")


if __name__ == "__main__":
    unittest.main()
