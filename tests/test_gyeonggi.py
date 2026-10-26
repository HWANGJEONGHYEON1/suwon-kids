import pathlib
import unittest
from datetime import date

from suwon_kids.sources import gyeonggi

HTML = (pathlib.Path(__file__).parent / 'fixtures/ggac_list.html').read_text(encoding='utf-8')


class GgacTest(unittest.TestCase):
    def test_only_suwon_venues(self):
        titles = [e.title for e in gyeonggi.parse_ggac(HTML)]
        self.assertIn('퓨전마당놀이 <춘향전>', titles)
        self.assertNotIn('「ON STAGE: 경기」 2026년 예술인기회소득확산사업', titles)  # 경기도서관
        self.assertFalse(any('꼬마별' in t for t in titles))  # 국악당(용인)

    def test_fields(self):
        ev = next(e for e in gyeonggi.parse_ggac(HTML) if e.title.startswith('퓨전마당놀이'))
        self.assertEqual((ev.start, ev.end), (date(2026, 10, 29), date(2026, 10, 30)))
        self.assertEqual(ev.url, 'https://www.ggac.or.kr/ggac/M0000155/show/view.do?idx=SM000198')
        self.assertEqual(ev.place, '경기아트센터 소극장')
        self.assertEqual(ev.host, '경기아트센터')
        self.assertIn('팔달구', ev.address)
        self.assertTrue(ev.id.startswith('ggac:'))

    def test_page_count(self):
        self.assertEqual(gyeonggi.last_page(HTML), 2)


if __name__ == '__main__':
    unittest.main()
