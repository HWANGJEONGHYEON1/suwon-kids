import pathlib
import unittest
from datetime import date

from suwon_kids.models import MallItem
from suwon_kids.sources import lotte

FIX = pathlib.Path(__file__).parent / 'fixtures'
P5 = (FIX / 'lotte_0406_news_p5.html').read_text(encoding='utf-8')
P1 = (FIX / 'lotte_0406_news_p1.html').read_text(encoding='utf-8')
P1_SUWON = (FIX / 'lotte_0349_news_p1.html').read_text(encoding='utf-8')
TODAY = date(2026, 11, 4)


class LotteTest(unittest.TestCase):
    def test_teletubbies_parsed(self):
        it = next(i for i in lotte.parse_list(P5, '0406', TODAY) if i.brand == '텔레토비')
        self.assertEqual((it.title, it.place, it.mall), ('가을 피크닉 Pop-Up', '잔디광장', '타임빌라스 의왕'))
        self.assertEqual((it.start, it.end), (date(2026, 10, 28), date(2026, 11, 8)))
        self.assertEqual(it.id, 'lotte:0406:SNM00000000000561714')
        self.assertEqual(it.url, 'https://www.lotteshopping.com/shpgnews/shpgnewsDetail?shpgNewsNo=SNM00000000000561714')
        self.assertEqual(it.source, 'lotte')

    def test_other_store_dropped(self):
        titles = [i.title for i in lotte.parse_list(P5, '0406', TODAY)]
        self.assertNotIn('적립 브랜드 안내', titles)       # 백화점 전점
        self.assertNotIn('콜라보 제품 출시', titles)       # 온라인
        self.assertNotIn('Meet New Breeze', [i.title for i in lotte.parse_list(P1_SUWON, '0349', TODAY)])  # 청량리점
        titles = [i.title for i in lotte.parse_list(P1, '0406', TODAY)]
        self.assertNotIn('K2/다이나핏/와이드앵글', titles)  # 일부 지점
        self.assertNotIn('CHRISTMAS MARKET', titles)       # 잠실점

    def test_brand_forms(self):
        items = {i.id: i for i in lotte.parse_list(P5, '0406', TODAY)}
        it = next(i for i in items.values() if i.brand == '노비스')  # 한 줄 + <br>
        self.assertEqual(it.title, '프리미엄 패딩 Pop-Up Open')
        it = next(i for i in items.values() if i.brand == '와이잭')  # 한 줄
        self.assertEqual(it.title, '프리미엄 컨템포러리 POP-UP')
        it = next(i for i in lotte.parse_list(P1_SUWON, '0349', TODAY) if '다니엘' in i.title)
        self.assertIsNone(it.brand)                                  # 대괄호 없음

    def test_suwon_place_skips_division(self):  # 지점 / 쇼핑몰 / 장소 세 칸
        it = next(i for i in lotte.parse_list(P1_SUWON, '0349', TODAY) if i.brand == '52토이즈')
        self.assertEqual((it.title, it.place), ('캐릭터 Pop-Up', '2F 무신사스탠다드 앞 특설행사장'))
        self.assertEqual((it.start, it.end), (date(2026, 11, 6), date(2026, 11, 19)))

    def test_open_ended_dropped(self):  # '11.3(화) OPEN'
        self.assertNotIn('택스 리펀 키오스크 안내', [i.title for i in lotte.parse_list(P1_SUWON, '0349', TODAY)])

    def test_period_explicit_year(self):
        self.assertEqual(lotte.parse_period('26.10.19(월) ~ 27.2.28(일)', TODAY), (date(2026, 10, 19), date(2027, 2, 28)))

    def test_period_whole_year(self):
        self.assertEqual(lotte.parse_period('1.6(화) ~ 12.31(목)', TODAY), (date(2026, 1, 6), date(2026, 12, 31)))

    def test_period_next_year_seen_in_december(self):
        self.assertEqual(lotte.parse_period('1.5(화) ~ 1.20(수)', date(2026, 12, 28)), (date(2027, 1, 5), date(2027, 1, 20)))

    def test_period_across_new_year(self):
        self.assertEqual(lotte.parse_period('12.20(일) ~ 1.10(일)', date(2026, 12, 28)), (date(2026, 12, 20), date(2027, 1, 10)))

    def test_period_open_is_none(self):
        self.assertIsNone(lotte.parse_period('11.3(화) OPEN', TODAY))

    def test_paging(self):
        self.assertEqual(lotte.paging(P5), (59, False))
        self.assertEqual(lotte.paging(P1_SUWON), (86, True))

    def test_fetch_cookie_then_pages(self):
        calls = []
        pages = iter([P1_SUWON, P5])  # 첫 쪽 hasNext Y, 둘째 쪽 N
        def get(url, headers=None, jar=None, data=None, **kw):
            calls.append((url, data))
            return b'' if 'store/main' in url else next(pages, P5).encode()
        lotte.fetch(TODAY, get=get)
        self.assertTrue(calls[0][0].endswith('store/main?cstrCd=0406'))
        self.assertIn(b'cntsTpCd=C00903', calls[1][1])
        self.assertIn(b'totalCnt=86', calls[2][1])  # 둘째 쪽부터 첫 응답의 totalCnt

    def test_fetch_all_fail_raises(self):
        def get(url, **kw):
            raise OSError('down')
        with self.assertRaises(OSError):
            lotte.fetch(TODAY, get=get)

    def test_fetch_one_failure_skipped(self):
        def get(url, headers=None, jar=None, data=None, **kw):
            if 'cstrCd=0406' in url:
                raise OSError('down')
            return b'' if 'store/main' in url else P1_SUWON.replace('"Y"', '"N"').encode()
        self.assertTrue(lotte.fetch(TODAY, get=get))


class MallItemTest(unittest.TestCase):
    def test_to_json_adds_address_and_iso_dates(self):
        d = MallItem('x', 'lotte', '타임빌라스 의왕', 't', None, date(2026, 11, 1), date(2026, 11, 2), 'p', 'u').to_json()
        self.assertEqual((d['start'], d['end']), ('2026-11-01', '2026-11-02'))
        self.assertEqual(d['address'], '경기도 의왕시 바라산로 1')
        self.assertIsNone(d['kind'])
