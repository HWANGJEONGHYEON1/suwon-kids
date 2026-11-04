import pathlib
import unittest
from datetime import date

from suwon_kids.sources import ak

FIX = pathlib.Path(__file__).parent / 'fixtures'
P1 = (FIX / 'ak_02_news_p1.html').read_text(encoding='utf-8')
TODAY = date(2026, 11, 4)


class AkTest(unittest.TestCase):
    def test_parsed(self):
        items = ak.parse_list(P1)
        self.assertEqual(len(items), 8)
        it = next(i for i in items if '[i store] 11월 프로모션' == i.title)
        self.assertEqual((it.place, it.start, it.end), ('AK& 2F', date(2026, 11, 1), date(2026, 11, 28)))
        self.assertEqual((it.mall, it.source), ('AK플라자 수원', 'ak'))
        self.assertTrue(it.id.startswith('ak:') and it.url.startswith('https://www.akplaza.com/board/news/view?store=02&seq='))

    def test_empty_page(self):
        self.assertEqual(ak.parse_list('<html><body>없음</body></html>'), [])

    def test_fetch_stops_at_empty_page(self):
        urls = []

        def get(url, **kw):
            urls.append(url)
            return P1.encode('utf-8') if url.endswith('page=1') else b'<html></html>'
        items = ak.fetch(TODAY, get=get)
        self.assertEqual(len(items), 8)
        self.assertEqual(urls, [f'https://www.akplaza.com/board/news/list?store=02&page={n}' for n in (1, 2)])

    def test_fetch_all_fail_raises(self):
        def get(url, **kw):
            raise OSError('down')
        with self.assertRaises(OSError):
            ak.fetch(TODAY, get=get)

    def test_fetch_one_failure_skipped(self):
        def get(url, **kw):
            if url.endswith('page=1'):
                raise OSError('down')
            return P1.encode('utf-8') if url.endswith('page=2') else b''
        self.assertTrue(ak.fetch(TODAY, get=get))


if __name__ == '__main__':
    unittest.main()
