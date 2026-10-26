import json
import pathlib
import unittest
from datetime import date

from suwon_kids.sources import starfield

ROWS = json.loads((pathlib.Path(__file__).parent / 'fixtures/starfield_list.json').read_text(encoding='utf-8'))['data']


class StarfieldTest(unittest.TestCase):
    def test_parse_dates_basic(self):
        self.assertEqual(starfield.parse_dates('11.7(토), 11.14(토)', date(2026, 10, 26)),
                         [date(2026, 11, 7), date(2026, 11, 14)])

    def test_parse_dates_year_wrap(self):
        self.assertEqual(starfield.parse_dates('12.26(토), 1.2(토)', date(2026, 12, 1)),
                         [date(2026, 12, 26), date(2027, 1, 2)])

    def test_title_strips_br(self):
        ev = starfield.to_events(ROWS[1])[0]
        self.assertEqual(ev.title, '별마당 도서관 10월 강연&공연 안내')

    def test_one_event_per_date(self):
        evs = starfield.to_events(ROWS[0])
        self.assertEqual(len(evs), 4)
        self.assertEqual(evs[0].id, 'starfield:EV202610231120213069:20261107')
        self.assertEqual(evs[0].place, '스타필드 수원')
        self.assertTrue(evs[0].image.startswith('https://www.starfield.co.kr/cdn/'))

    def test_unparsable_dates_use_post_period(self):
        row = dict(ROWS[0], evtStrtDtTxt='매주 주말')
        evs = starfield.to_events(row)
        self.assertEqual([(e.start, e.end) for e in evs], [(date(2026, 10, 26), date(2026, 11, 29))])


if __name__ == '__main__':
    unittest.main()
