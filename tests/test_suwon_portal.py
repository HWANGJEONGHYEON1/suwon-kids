import json
import pathlib
import unittest
from datetime import date

from suwon_kids.sources import suwon_portal

ROWS = json.loads((pathlib.Path(__file__).parent / 'fixtures/portal_list.json').read_text(encoding='utf-8'))['dataList']


class SuwonPortalTest(unittest.TestCase):
    def test_parse_date(self):
        self.assertEqual(suwon_portal.parse_date('2026-10-09(금)'), date(2026, 10, 9))
        self.assertIsNone(suwon_portal.parse_date(None))
        self.assertIsNone(suwon_portal.parse_date(''))

    def test_parse_date_no_dashes(self):
        self.assertEqual(suwon_portal.parse_date('20231013(금)'), date(2023, 10, 13))

    def test_to_events_skips_undated(self):
        rows = [dict(ROWS[0], startDt='미정'), ROWS[1]]
        self.assertEqual([e.title for e in suwon_portal.to_events(rows)], [ROWS[1]['cultureNm'].strip()])

    def test_to_event_fields(self):
        row = ROWS[0]
        ev = suwon_portal.to_event(row)
        self.assertTrue(ev.id.startswith('suwon:'))
        self.assertEqual(ev.title, row['cultureNm'].strip())
        self.assertEqual(ev.place, row['ctrLocation'])
        self.assertEqual(ev.url, f"https://www.suwon.go.kr/culture/ingCultureView.do?ctrSeqNo={row['ctrSeqNo']}")

    def test_end_missing_uses_start(self):
        ev = suwon_portal.to_event(ROWS[2])
        self.assertEqual(ev.end, ev.start)


class PortalDetailTest(unittest.TestCase):
    def test_fixture_price(self):
        page = (pathlib.Path(__file__).parent / 'fixtures/portal_detail.html').read_text(encoding='utf-8')
        self.assertEqual(suwon_portal.parse_detail(page)['price'], '무료')

    def test_time_and_program(self):
        row = '<th scope="row">{}</th><td>{}</td>'
        page = row.format('행사시간', '13:00 ~ 17:00') + row.format('행사개요', '? 주요내용: 분장대회, 축하공연(크라잉넛, 바다) 등')
        d = suwon_portal.parse_detail(page)
        self.assertEqual((d['time'], d['program']), ('13:00 ~ 17:00', '분장대회, 축하공연(크라잉넛, 바다) 등'))
        self.assertEqual(suwon_portal.parse_detail(row.format('행사시간', '01:00 ~ 01:00'))['time'], '')


if __name__ == '__main__':
    unittest.main()
