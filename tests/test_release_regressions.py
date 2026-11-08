"""作者：Wangyuan；日期：2026-11-08。职责：防止多行号码被拼接成新号码。"""
import unittest
from phone import NumberPolicy, normalize


class NumberBoundaryTests(unittest.TestCase):
    def test_internal_record_separators_never_join_numbers(self) -> None:
        policy = NumberPolicy((8,))
        for separator in ["\n", "\r", "\t", "\u2028", "\u2029"]:
            with self.subTest(separator=repr(separator)):
                self.assertFalse(normalize("7123" + separator + "7456", policy)["valid"])
        self.assertTrue(normalize("7123 7456", policy)["valid"])
