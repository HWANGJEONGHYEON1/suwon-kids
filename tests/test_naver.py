import json
import unittest
from datetime import date

from suwon_kids.sources import naver

TODAY = date(2026, 10, 28)  # 수요일, 이번 주는 11/1(일)까지


def item(title, desc, link, pub='Wed, 28 Oct 2026 08:32:00 +0900'):
    return {'title': title, 'description': desc, 'link': link, 'originallink': link, 'pubDate': pub}


WALK = item('안양시, 이달 31일 &apos;<b>시민과 함께하는 행복 걷기대회</b>&apos; 개최',
            '안양시는 31일 오전 8시 30분 학운공원 운동장에서 출발하는 행복 걷기대회를 연다. 사전 신청 없이 가족 누구나 참여할 수 있다.',
            'https://news.example/walk')
OLD = item('용인 축제 성료', '지난달 열린 축제가 막을 내렸다.', 'https://news.example/old', 'Mon, 01 Sep 2026 09:00:00 +0900')


def fake_search(query):
    return {'items': [WALK, OLD]}  # 같은 기사가 여러 검색어에 나온다


def fake_gen(rows):
    return lambda prompt: '```json\n' + json.dumps(rows, ensure_ascii=False) + '\n```'


ROW = {'n': 0, 'title': '시민과 함께하는 행복 걷기대회', 'start': '2026-10-31', 'end': '2026-10-31', 'time': '08:30',
       'place': '학운공원 운동장', 'city': '안양', 'summary': '학운공원 출발 걷기대회'}

ART = {'title': '의왕 팝업', 'text': '31일 텔레토비 팝업이 열린다.', 'link': 'https://news.example/tt', 'pub': TODAY}


class NaverTest(unittest.TestCase):
    def test_articles_dedupe_and_recent(self):
        arts = naver.articles([fake_search('a'), fake_search('b')], TODAY)
        self.assertEqual([a['link'] for a in arts], ['https://news.example/walk'])
        self.assertEqual(arts[0]['title'], "안양시, 이달 31일 '시민과 함께하는 행복 걷기대회' 개최")

    def test_fetch_builds_event(self):
        evs = naver.fetch(TODAY, search=fake_search, gen=fake_gen([ROW]))
        self.assertEqual(len(evs), 1)
        ev = evs[0]
        self.assertEqual((ev.title, ev.start, ev.time, ev.place), ('시민과 함께하는 행복 걷기대회', date(2026, 10, 31), '08:30', '학운공원 운동장'))
        self.assertEqual(ev.address, '경기도 안양시 학운공원 운동장')
        self.assertEqual(ev.url, 'https://news.example/walk')
        self.assertEqual(ev.target, '누구나')
        self.assertEqual(ev.summary, '학운공원 출발 걷기대회')

    def test_date_not_in_article_dropped(self):
        evs = naver.fetch(TODAY, search=fake_search, gen=fake_gen([{**ROW, 'start': '2026-11-01', 'end': '2026-11-01'}]))
        self.assertEqual(evs, [])

    def test_bad_rows_dropped(self):
        rows = [{**ROW, 'city': '서울'}, {**ROW, 'n': 5}, {**ROW, 'place': ''}, {**ROW, 'start': '10월 31일'}, 'x']
        self.assertEqual(naver.fetch(TODAY, search=fake_search, gen=fake_gen(rows)), [])

    def test_outside_week_dropped(self):
        art = item('오산 축제', '오산시는 11월 7일 축제를 연다.', 'https://news.example/osan')
        row = {**ROW, 'start': '2026-11-07', 'end': '2026-11-07', 'city': '오산'}
        self.assertEqual(naver.fetch(TODAY, search=lambda q: {'items': [art]}, gen=fake_gen([row])), [])

    def test_unverified_summary_removed(self):
        evs = naver.fetch(TODAY, search=fake_search, gen=fake_gen([{**ROW, 'summary': '불꽃놀이와 드론쇼'}]))
        self.assertIsNone(evs[0].summary)

    def test_dongtan_address(self):
        art = item('동탄 호수공원 가을 축제', '화성시는 11월 1일 동탄호수공원에서 가족 축제를 연다.', 'https://news.example/dt')
        row = {**ROW, 'title': '동탄 가을 축제', 'start': '2026-11-01', 'end': '2026-11-01', 'place': '동탄호수공원', 'city': '동탄'}
        evs = naver.fetch(TODAY, search=lambda q: {'items': [art]}, gen=fake_gen([row]))
        self.assertEqual(evs[0].address, '경기도 화성시 동탄구 동탄호수공원')

    def test_garbage_reply_is_empty(self):
        self.assertEqual(naver.fetch(TODAY, search=fake_search, gen=lambda p: '죄송합니다'), [])

    def test_all_searches_failed_raises(self):
        def down(q):
            raise OSError('401')
        with self.assertRaises(OSError):
            naver.fetch(TODAY, search=down, gen=fake_gen([]))

    def test_mentions(self):
        self.assertTrue(naver.mentions('이달 31일 개최', date(2026, 10, 31)))
        self.assertTrue(naver.mentions('10.31(토) 개최', date(2026, 10, 31)))
        self.assertFalse(naver.mentions('131일', date(2026, 10, 31)))
        self.assertFalse(naver.mentions('10월 3일', date(2026, 10, 31)))
        self.assertFalse(naver.mentions('지난 9월 28일 열린 축제', date(2026, 10, 28)))
        self.assertFalse(naver.mentions('9월28일', date(2026, 10, 28)))
        self.assertTrue(naver.mentions('10월 28일', date(2026, 10, 28)))

    def test_same_event_different_names_merged(self):
        rows = [{**ROW, 'title': '행복 걷기대회', 'place': '안양천'}, ROW, {**ROW, 'title': '석수본페스타', 'place': '석수본동'}]
        evs = naver.fetch(TODAY, search=fake_search, gen=fake_gen(rows))
        self.assertEqual([e.title for e in evs], ['행복 걷기대회', '석수본페스타'])

    def test_failed_batch_keeps_others(self):
        arts = [item(f'안양 축제 {i}', '31일 학운공원 운동장', f'https://news.example/{i}') for i in range(naver.BATCH + 1)]
        calls = []

        def gen(prompt):
            calls.append(1)
            if len(calls) == 2:
                raise TimeoutError
            return json.dumps([ROW])
        evs = naver.fetch(TODAY, search=lambda q: {'items': arts}, gen=gen)
        self.assertEqual(len(evs), 1)

    def test_all_batches_failed_raises(self):
        def gen(prompt):
            raise TimeoutError
        with self.assertRaises(TimeoutError):
            naver.fetch(TODAY, search=fake_search, gen=gen)

    def test_mall_event_dropped_from_city_tab(self):  # 백화점 7곳 행사는 백화점 탭에 있다
        art = ART
        title = '텔레토비 팝업스토어'
        for place in ('롯데프리미엄아울렛 의왕점', '롯데아울렛 의왕점', '스타필드 수원'):
            row = {**ROW, 'title': title, 'place': place, 'city': '의왕'}
            self.assertIsNone(naver.to_event(row, art), place)
        kept = naver.to_event({**ROW, 'title': title, 'place': '롯데백화점 동탄', 'city': '동탄'}, art)
        self.assertEqual(kept.place, '롯데백화점 동탄')

    def test_sponsor_name_in_title_not_mall(self):  # 제목의 '롯데 후원'만으로 백화점 행사로 보지 않는다
        row = {**ROW, 'title': '롯데 후원 의왕 가족축제', 'place': '의왕 왕송호수공원', 'city': '의왕'}
        self.assertEqual(naver.to_event(row, ART).place, '의왕 왕송호수공원')

    def test_mall_place_names(self):
        for place in ('타임빌라스 수원', '롯데몰 광교', '스타필드수원', '롯데백화점 평촌점', '현대백화점 판교점', 'AK플라자 수원'):
            self.assertTrue(naver.is_mall_event(place), place)
        for place in ('왕송호수공원', '롯데백화점 동탄', '수원 화성행궁', 'BAKERY 수원', 'LAKE PARK 수원'):
            self.assertFalse(naver.is_mall_event(place), place)

    def _e(self, title, start=date(2026, 10, 31), end=None, city='동탄', place='장소'):
        return naver.Event(f'naver:{title}', 'naver', title, start, end or start, None, place, f'{naver.PLACES[city]} {place}',
                           'https://x', '누구나')

    def test_same_shared_key_token(self):
        self.assertTrue(naver.same(self._e('MLB키즈 겨울 팝업'), self._e('MLB키즈 팝업스토어')))
        self.assertTrue(naver.same(self._e('텔레토비 팝업스토어'), self._e('텔레토비와 함께하는 가을 피크닉')))

    def test_same_needs_overlap_and_city(self):
        a = self._e('MLB키즈 겨울 팝업', date(2026, 10, 26), date(2026, 10, 28))
        self.assertFalse(naver.same(a, self._e('MLB키즈 팝업스토어', date(2026, 10, 30))))
        self.assertTrue(naver.same(a, self._e('MLB키즈 팝업스토어', date(2026, 10, 28), date(2026, 10, 30))))
        self.assertFalse(naver.same(self._e('MLB키즈 팝업'), self._e('MLB키즈 팝업', city='용인')))

    def test_generic_word_only_not_same(self):
        self.assertFalse(naver.same(self._e('동탄 가을 축제'), self._e('호수공원 사랑 축제')))
        self.assertFalse(naver.same(self._e('가을 걷기대회'), self._e('단풍 걷기대회 행사')))


    def test_same_place_token_not_key(self):  # 같은 공원에서 열리는 다른 행사
        self.assertFalse(naver.same(self._e('동탄호수공원 국화 축제', place='동탄호수공원'),
                                    self._e('동탄호수공원 재즈 축제', place='동탄호수공원')))
        self.assertFalse(naver.same(self._e('왕송호수 국화 축제', place='왕송호수공원'), self._e('왕송호수 재즈 축제', place='왕송호수공원')))

    def test_venue_suffix_token_not_key(self):
        self.assertFalse(naver.same(self._e('시민광장 국화 축제', place='A'), self._e('시민광장 재즈 축제', place='B')))
        self.assertTrue(naver.same(self._e('MLB키즈 겨울 팝업', place='롯데백화점 동탄'), self._e('MLB키즈 팝업스토어', place='롯데백화점 동탄')))


if __name__ == '__main__':
    unittest.main()
