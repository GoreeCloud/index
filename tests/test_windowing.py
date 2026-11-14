"""Pure geometry contract for GoreeCloud Index's native GTK palette."""

import unittest

from goreecloud_index.windowing import (
    DEFAULT_PALETTE_SIZE, MIN_PALETTE_SIZE, palette_startup_size,
    palette_startup_size_for_monitors,
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

    
class MultiMonitorPaletteTests(unittest.TestCase):
    def test_mixed_monitor_order_does_not_change_initial_palette(self):
        large, small = (3840, 2160), (640, 360)
        for monitors in ((large, small), (small, large)):
            with self.subTest(monitors=monitors):
                self.assertEqual(palette_startup_size_for_monitors(monitors), (576, 324))

    def test_smallest_dimensions_from_different_monitors(self):
        self.assertEqual(
            palette_startup_size_for_monitors(((900, 1600), (2000, 390))),
            (660, 351),
        )

    def test_invalid_and_missing_monitor_geometry_uses_safe_defaults(self):
        self.assertEqual(
            palette_startup_size_for_monitors(((0, 0), (1920, 1080), (-8, 500))),
            DEFAULT_PALETTE_SIZE,
        )
        self.assertEqual(palette_startup_size_for_monitors(()), DEFAULT_PALETTE_SIZE)
        self.assertEqual(
            palette_startup_size_for_monitors(((True, 768), (None, 800))),
            DEFAULT_PALETTE_SIZE,
        )


class QtCompactWindowContractTests(unittest.TestCase):
    """Opt-in Qt client uses the same conservative GTK-tested geometry rules."""

    def test_qt_preferred_footprint_on_large_and_small_screens(self):
        qt = (660, 488)
        self.assertEqual(palette_startup_size_for_monitors(
            [(1920, 1080)], preferred_size=qt), qt)
        self.assertEqual(palette_startup_size_for_monitors(
            [(640, 360)], preferred_size=qt), (576, 324))
        self.assertEqual(palette_startup_size_for_monitors(
            [(3840, 2160), (640, 360)], preferred_size=qt), (576, 324))
        self.assertEqual(palette_startup_size_for_monitors(
            [(640, 360), (3840, 2160)], preferred_size=qt), (576, 324))

    def test_qt_uses_each_monitor_axis_and_handles_unavailable_screen(self):
        qt = (660, 488)
        self.assertEqual(palette_startup_size_for_monitors(
            [(900, 1600), (2000, 390)], preferred_size=qt),
            (660, 351))
        self.assertEqual(palette_startup_size_for_monitors(
            [], preferred_size=qt), qt)
        self.assertEqual(palette_startup_size_for_monitors(
            [(0, 0), (True, 800)], preferred_size=qt), qt)

    def test_custom_preferred_sizes_reject_invalid_values(self):
        for preferred in ((0, 488), (660, 250), (True, 488),
                          (660,), [660, 488], ("660", 488)):
            with self.subTest(preferred=preferred):
                with self.assertRaises(ValueError):
                    palette_startup_size_for_monitors(
                        [(1920, 1080)], preferred_size=preferred)


if __name__ == "__main__":
    unittest.main()
