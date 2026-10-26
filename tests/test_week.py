import unittest
from datetime import date, timedelta

from suwon_kids import week
from suwon_kids.models import Event


def ev(start, end):
    return Event('x', 'suwon', 't', start, end, None, '', '', '', '누구나')


class WeekTest(unittest.TestCase):
    def test_this_week_monday(self):
        self.assertEqual(week.this_week(date(2026, 10, 26)), (date(2026, 10, 26), date(2026, 11, 1)))

    def test_this_week_sunday(self):
        self.assertEqual(week.this_week(date(2026, 11, 1)), (date(2026, 11, 1), date(2026, 11, 1)))

    def test_overlaps_edge(self):
        rng = week.this_week(date(2026, 10, 26))
        self.assertTrue(week.overlaps(ev(date(2026, 10, 1), date(2026, 10, 26)), rng))
        self.assertFalse(week.overlaps(ev(date(2026, 11, 2), date(2026, 11, 2)), rng))
        self.assertFalse(week.overlaps(ev(date(2026, 10, 1), date(2026, 10, 25)), rng))

    def test_is_long(self):
        s = date(2026, 10, 1)
        self.assertTrue(week.is_long(ev(s, s + timedelta(days=31))))
        self.assertFalse(week.is_long(ev(s, s + timedelta(days=30))))


if __name__ == '__main__':
    unittest.main()
