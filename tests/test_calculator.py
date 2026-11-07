from __future__ import annotations

import unittest

from goreecloud_index.calculator import calculate


class CalculatorTests(unittest.TestCase):
    def test_arithmetic(self) -> None:
        self.assertEqual(calculate("(2 + 3) * 4"), "20")
        self.assertEqual(calculate("2 ** 3"), "8")
        self.assertEqual(calculate("15% of 85"), "12.75")

    def test_unit_conversions(self) -> None:
        self.assertEqual(calculate("5 km in m"), "5000 m")
        self.assertEqual(calculate("32 F to C"), "0 C")
        self.assertEqual(calculate("1 MiB to KiB"), "1024 KiB")

    def test_non_calculator_and_unsafe_expressions(self) -> None:
        self.assertIsNone(calculate("my document"))
        self.assertIsNone(calculate("__import__('os').system('true')"))
        self.assertIsNone(calculate("1 / 0"))
        self.assertIsNone(calculate("9 ** 999"))
        self.assertIsNone(calculate("1+2; rm -rf /"))


if __name__ == "__main__":
    unittest.main()
