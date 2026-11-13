"""周报索引的周期日计算：周六当天算本周，其余日子回到最近一个已过的周六。"""
from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_weekly_index import most_recent_saturday  # noqa: E402


class WeeklyIndexDatesTest(unittest.TestCase):
    def test_saturday_is_itself(self):
        self.assertEqual(most_recent_saturday(dt.date(2026, 11, 14)),
                         dt.date(2026, 11, 14))

    def test_friday_returns_previous_saturday(self):
        self.assertEqual(most_recent_saturday(dt.date(2026, 11, 13)),
                         dt.date(2026, 11, 7))

    def test_sunday_returns_yesterday(self):
        self.assertEqual(most_recent_saturday(dt.date(2026, 11, 15)),
                         dt.date(2026, 11, 14))

    def test_monday_returns_two_days_back(self):
        self.assertEqual(most_recent_saturday(dt.date(2026, 11, 16)),
                         dt.date(2026, 11, 14))

    def test_result_is_always_a_saturday(self):
        for offset in range(14):
            day = dt.date(2026, 11, 1) + dt.timedelta(days=offset)
            self.assertEqual(most_recent_saturday(day).weekday(), 5)


if __name__ == "__main__":
    unittest.main()
