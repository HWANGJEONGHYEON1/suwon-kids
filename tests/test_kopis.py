import pathlib
import unittest
from datetime import date

from suwon_kids.sources import kopis

FX = pathlib.Path(__file__).parent / 'fixtures'
LIST, DETAIL, PLACE = ((FX / f).read_text(encoding='utf-8') for f in ('kopis_list.xml', 'kopis_detail.xml', 'kopis_place.xml'))
TODAY = date(2026, 10, 27)


def fake_get(path, **params):
    if path == 'pblprfr':
        return LIST if params['signgucodesub'] == kopis.CITIES['화성'] else '<dbs></dbs>'
    if path.startswith('pblprfr/'):
        return DETAIL
    return PLACE


class KopisTest(unittest.TestCase):
    def test_rows(self):
        r = kopis.rows(LIST)
        self.assertEqual([x['mt20id'] for x in r], ['PF303862', 'PF302575'])

    def test_to_event(self):
        ev = kopis.to_event(kopis.rows(LIST)[0], kopis.rows(DETAIL)[0], '경기도 화성시 동탄구 경기동로 468-5 (장지동)')
        self.assertEqual(ev.title, '할로윈 매직쇼')
        self.assertEqual(ev.place, '더퍼포머씨어터')
        self.assertEqual((ev.start, ev.end), (date(2026, 10, 31), date(2026, 11, 1)))
        self.assertEqual(ev.time, '토 14:00·19:00 / 일 11:00·15:00')
        self.assertEqual(ev.age, '전체 관람가')
        self.assertEqual(ev.price, '전석 50,000원')
        self.assertEqual(ev.booking, 'https://booking.naver.com/booking/12/bizes/887872')
        self.assertTrue(ev.image.startswith('https://kopis.or.kr/upload/pfmPoster/'))
        self.assertEqual(ev.url, 'https://kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF303862')
        self.assertEqual(ev.target, '어린이')

    def test_short_time_range(self):
        self.assertEqual(kopis.short_time('토요일 ~ 일요일(11:00,14:00,16:30)'), '토 ~ 일 11:00·14:00·16:30')

    def test_long_time_cut(self):
        ev = kopis.to_event(kopis.rows(LIST)[0], {'dtguidance': '가' * 50}, '')
        self.assertEqual(ev.time, '가' * kopis.MAX_TIME + '…')

    def test_fetch_uses_place_address(self):
        evs = kopis.fetch(TODAY, get=fake_get)
        self.assertEqual(len(evs), 2)
        self.assertTrue(all(e.address.startswith('경기도 화성시 동탄구') for e in evs))

    def test_fetch_detail_failure_falls_back_to_city(self):
        def broken(path, **params):
            if path == 'pblprfr':
                return fake_get(path, **params)
            raise OSError('down')
        evs = kopis.fetch(TODAY, get=broken)
        self.assertEqual([e.address for e in evs], ['경기도 화성시', '경기도 화성시'])
        self.assertIsNone(evs[0].time)

    def test_fetch_retries_and_skips_failed_city(self):
        calls = []

        def flaky(path, **params):
            if path == 'pblprfr':
                code = params['signgucodesub']
                calls.append(code)
                if code == kopis.CITIES['수원']:
                    raise OSError('400')  # 수원은 두 번 다 실패
                if code == kopis.CITIES['화성'] and calls.count(code) == 1:
                    raise OSError('400')  # 화성은 재시도에서 성공
            return fake_get(path, **params)
        evs = kopis.fetch(TODAY, get=flaky)
        self.assertEqual(len(evs), 2)
        self.assertEqual(calls.count(kopis.CITIES['수원']), 2)

    def test_fetch_all_cities_failed_raises(self):
        def down(path, **params):
            raise OSError('400')
        with self.assertRaises(OSError):
            kopis.fetch(TODAY, get=down)


if __name__ == '__main__':
    unittest.main()
