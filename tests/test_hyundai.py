import json
import pathlib
import unittest
from datetime import date
from urllib.parse import parse_qs, urlparse

from suwon_kids.sources import hyundai

FIX = pathlib.Path(__file__).parent / 'fixtures'
DATA = json.loads((FIX / 'hyundai_01.json').read_text(encoding='utf-8'))
PAGE_HTML = (FIX / 'hyundai_page.html').read_text(encoding='utf-8')
TODAY = date(2026, 11, 4)


class HyundaiTest(unittest.TestCase):
    def test_dm_code(self):
        self.assertEqual(hyundai.dm_code(PAGE_HTML), 'D4802610463776')

    def test_dm_code_missing(self):
        with self.assertRaises(ValueError):
            hyundai.dm_code('<html></html>')

    def test_kids_popup_parsed(self):
        it = next(i for i in hyundai.parse(DATA) if '리틀티니' in i.title)
        self.assertEqual(it.title, '[POP-UP STORE] 리틀티니')
        self.assertEqual(it.place, '5층 캐리마켓 옆')
        self.assertEqual((it.start, it.end), (date(2026, 10, 28), date(2026, 11, 8)))
        self.assertEqual((it.id, it.mall, it.source), ('hyundai:E4802610512336', '현대백화점 판교', 'hyundai'))
        self.assertEqual(it.url, 'https://link.ehyundai.com/PaXJ/xzjn8psl')
        self.assertIsNone(it.brand)

    def test_no_end_dropped(self):  # 피레넥스: 끝 날짜 빈 값
        self.assertFalse(any('피레넥스' in i.title for i in hyundai.parse(DATA)))

    def test_no_floor_place(self):  # 층 '미입력'은 장소에 쓰지 않는다
        self.assertFalse(any(i.place.startswith('미입력') for i in hyundai.parse(DATA)))

    def test_title_whitespace_collapsed(self):
        titles = [i.title for i in hyundai.parse(DATA)]
        self.assertIn('TUDOR Born To Race 팝업', titles)
        self.assertFalse(any('\n' in t or '  ' in t or t != t.strip() for t in titles))

    def test_place_variants(self):
        def item(**kw):
            return {'evntCrdCd': 'X', 'evntCrdNm': 'a', 'storeCd': '480', 'expsEvntStartDt': '20261101000000',
                    'expsEvntEndDt': '20261102000000', **kw}
        out = {i.id: i.place for i in hyundai.parse({'result': {'items': [
            item(evntCrdCd='A', evntFlrCd={'label': '미입력'}, evntPlceNm='열린광장'),
            item(evntCrdCd='B', evntFlrCd={'label': '3층'}, evntPlceNm=''),
            item(evntCrdCd='C', evntFlrCd={'label': '미입력'}, evntPlceNm=''),
            item(evntCrdCd='D', evntPlceNm='  '),
        ]}})}
        self.assertEqual(out, {'hyundai:A': '열린광장', 'hyundai:B': '3층', 'hyundai:C': '', 'hyundai:D': ''})

    def test_missing_dates_and_url_fallback(self):
        base = {'evntCrdCd': 'X', 'evntCrdNm': 'a', 'storeCd': '480'}
        parse = lambda **kw: hyundai.parse({'result': {'items': [{**base, **kw}]}})
        self.assertEqual(parse(), [])
        self.assertEqual(parse(expsEvntStartDt='　', expsEvntEndDt='20261102000000'), [])
        self.assertEqual(parse(expsEvntStartDt='20261101000000', expsEvntEndDt=None), [])
        it = parse(expsEvntStartDt='20261101000000', expsEvntEndDt='20261102000000', onelink='')[0]
        self.assertEqual(it.url, hyundai.PAGE)

    def test_other_branch_events_dropped(self):  # 본사(110) 캠페인은 trgtStoreCd에 480이 있어도 판교 행사가 아니다
        titles = [i.title for i in hyundai.parse(DATA)]
        self.assertFalse(any('어린이그림대회' in t or 'Christmas' in t for t in titles))
        base = {'evntCrdCd': 'X', 'evntCrdNm': 'a', 'trgtStoreCd': '480', 'expsEvntStartDt': '20261101000000',
                'expsEvntEndDt': '20261102000000'}
        parse = lambda **kw: hyundai.parse({'result': {'items': [{**base, **kw}]}})
        self.assertEqual(parse(storeCd='110'), [])
        self.assertEqual(parse(), [])
        self.assertEqual(len(parse(storeCd='480')), 1)

    def test_parse_empty(self):
        self.assertEqual(hyundai.parse({}), [])
        self.assertEqual(hyundai.parse({'result': {'items': None}}), [])

    def test_fetch(self):
        calls, types = [], []

        def fake(url, **kw):
            calls.append(url)
            if url == hyundai.PAGE:
                return PAGE_HTML.encode('utf-8')
            q = parse_qs(urlparse(url).query)
            self.assertEqual(q['apiID'], ['ifAppHdcms012'])
            p = parse_qs(q['param'][0])
            self.assertEqual((p['mblDmCd'], p['pageSize'], p['page']), (['D4802610463776'], ['50'], ['1']))
            types.append(p['evntCrdTypeCd'][0])
            return json.dumps(DATA).encode('utf-8')

        out = hyundai.fetch(TODAY, get=fake)
        self.assertEqual(len(calls), 3)
        self.assertEqual(types, ['01', '03'])
        self.assertGreater(len(out), 0)

    def test_fetch_one_type_fails(self):
        def fake(url, **kw):
            if url == hyundai.PAGE:
                return PAGE_HTML.encode('utf-8')
            if 'evntCrdTypeCd%3D03' in url:
                raise OSError('boom')
            return json.dumps(DATA).encode('utf-8')
        self.assertGreater(len(hyundai.fetch(TODAY, get=fake)), 0)

    def test_fetch_all_fail_raises(self):
        def fake(url, **kw):
            if url == hyundai.PAGE:
                return PAGE_HTML.encode('utf-8')
            raise OSError('boom')
        with self.assertRaises(OSError):
            hyundai.fetch(TODAY, get=fake)


if __name__ == '__main__':
    unittest.main()
