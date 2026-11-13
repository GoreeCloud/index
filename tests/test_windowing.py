"""Pure geometry contract for GoreeCloud Index's native GTK palette."""

import unittest

from goreecloud_index.windowing import (
    DEFAULT_PALETTE_SIZE, MIN_PALETTE_SIZE, palette_startup_size,
)


class PaletteStartupTests(unittest.TestCase):
    def test_normal_monitor_preserves_existing_compact_default(self):
        self.assertEqual(palette_startup_size(1024, 768), DEFAULT_PALETTE_SIZE)

    def test_laptop_monitor_preserves_existing_compact_default(self):
        self.assertEqual(palette_startup_size(1366, 768), DEFAULT_PALETTE_SIZE)

    def test_low_resolution_monitor_reduces_normal_window(self):
        self.assertEqual(palette_startup_size(640, 360), (576, 324))

    def test_compact_layout_floor_for_very_small_displays(self):
        self.assertEqual(palette_startup_size(320, 240), MIN_PALETTE_SIZE)

    def test_unavailable_geometry_falls_back_without_immersive_behavior(self):
        for dims in ((0, 0), (-1, 720), (800, -1)):
            with self.subTest(dims=dims):
                self.assertEqual(palette_startup_size(*dims), DEFAULT_PALETTE_SIZE)


if __name__ == "__main__":
    unittest.main()
