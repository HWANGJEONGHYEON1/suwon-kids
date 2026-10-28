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


if __name__ == '__main__':
    unittest.main()
