import json
import pathlib
import unittest
from datetime import date

from suwon_kids.sources import tourapi

FX = pathlib.Path(__file__).parent / 'fixtures'
FEST = json.loads((FX / 'tour_festival.json').read_text(encoding='utf-8'))['response']['body']
COMMON = json.loads((FX / 'tour_common.json').read_text(encoding='utf-8'))['response']['body']
TODAY = date(2026, 11, 16)  # 픽스처 첫 행사(11.21~22)가 들어가는 주


def near(item, addr='경기도 안양시 만안구 예술공원로 180 (안양동)'):
    return {**item, 'addr1': addr}


class TourTest(unittest.TestCase):
    def test_items_single_dict(self):
        self.assertEqual(len(tourapi.items({'items': {'item': {'contentid': '1'}}})), 1)
        self.assertEqual(tourapi.items({'items': ''}), [])

    def test_homepage(self):
        self.assertEqual(tourapi.homepage('www.ricedessertfesta.com'), 'https://www.ricedessertfesta.com')
        self.assertEqual(tourapi.homepage('<a href="http://a.kr/x" target="_blank">a.kr</a>'), 'http://a.kr/x')
        self.assertEqual(tourapi.homepage('공식 홈페이지 https://www.apap.or.kr'), 'https://www.apap.or.kr')
        self.assertIsNone(tourapi.homepage('공식 홈페이지 없음'))
        self.assertIsNone(tourapi.homepage(''))

    def test_to_event(self):
        ev = tourapi.to_event(tourapi.items(FEST)[0], None)
        self.assertEqual(ev.title, '경기미 디저트 페스타')
        self.assertEqual((ev.start, ev.end), (date(2026, 11, 21), date(2026, 11, 22)))
        self.assertTrue(ev.url.startswith('https://search.naver.com/'))

    def test_fetch_near_only(self):
        first = tourapi.items(FEST)[0]
        body = {'items': {'item': [first, near(first)]}, 'totalCount': 2}
        get = lambda op, **p: body if op == 'searchFestival2' else COMMON
        evs = tourapi.fetch(TODAY, get=get)
        self.assertEqual(len(evs), 1)
        self.assertIn('안양시', evs[0].address)
        self.assertEqual(evs[0].url, 'https://www.ricedessertfesta.com')

    def test_fetch_skips_after_week(self):
        body = {'items': {'item': [near(tourapi.items(FEST)[0])]}, 'totalCount': 1}
        self.assertEqual(tourapi.fetch(date(2026, 10, 27), get=lambda op, **p: body), [])


if __name__ == '__main__':
    unittest.main()
