import json
import pathlib
import unittest
from datetime import date

from suwon_kids.sources import starfield

ROWS = json.loads((pathlib.Path(__file__).parent / 'fixtures/starfield_list.json').read_text(encoding='utf-8'))['data']
BRAND = json.loads((pathlib.Path(__file__).parent / 'fixtures/starfield_brand.json').read_text(encoding='utf-8'))['data']


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

    def test_brand_items(self):
        items = starfield.brand_items(BRAND)
        audi = next(i for i in items if i.title == '아우디 A6 전시 팝업')
        self.assertEqual((audi.start, audi.end, audi.mall), (date(2026, 10, 30), date(2026, 11, 8), '스타필드 수원'))
        self.assertTrue(audi.url.startswith('https://www.starfield.co.kr/suwon/eventBenefit/brand/EV'))
        self.assertEqual((audi.id, audi.source, audi.place), ('starfield-brand:EV202610281449373095', 'starfield', ''))

    def test_brand_permanent_dropped(self):  # 2017.01.01 ~ 2999.12.31 상시 안내
        titles = [i.title for i in starfield.brand_items(BRAND)]
        self.assertNotIn('땡겨요 QR 주문', titles)
        self.assertEqual(len(titles), 9)

    def test_brand_title_strips_br(self):
        titles = [i.title for i in starfield.brand_items(BRAND)]
        self.assertIn('스타필드 온라인몰 G마켓 빅스마일데이', titles)
        self.assertIn('신한/삼성/농협/국민카드 (모든 BC카드 제외) 구매 고객 혜택', titles)

    def test_fetch_brand_pages(self):
        calls = []

        def get(url, headers=None, jar=None, **kw):
            calls.append(url)
            if url.startswith(starfield.BRAND_API):
                page = int(url.rsplit('=', 1)[1])
                return json.dumps({'data': BRAND if page == 1 else BRAND[:1],
                                   'paginationInfo': {'totalPageCount': 2}}).encode()
            return b''
        items = starfield.fetch_brand(date(2026, 11, 4), get=get)
        self.assertEqual(calls[0], f'{starfield.SITE}/suwon/eventBenefit/brand')
        self.assertEqual(calls[1:], [starfield.BRAND_API + '1', starfield.BRAND_API + '2'])
        self.assertEqual(len(items), 10)

    def test_fetch_brand_all_fail_raises(self):
        def get(url, **kw):
            raise OSError('down')
        with self.assertRaises(OSError):
            starfield.fetch_brand(date(2026, 11, 4), get=get)


if __name__ == '__main__':
    unittest.main()
