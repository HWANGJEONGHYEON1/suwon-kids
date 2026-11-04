import email.utils
import json
import unittest
from datetime import date, datetime, timezone

from suwon_kids.sources import mall_news

TODAY = date(2026, 11, 4)
ART = {'title': 'MLB키즈, 스타필드 수원서 체험형 팝업', 'text': '11월 6일부터 15일까지 스타필드 수원 1층에서 연다',
       'link': 'https://news.example/1', 'pub': date(2026, 10, 21)}


def row(**kw):
    return {'n': 0, 'mall': '스타필드 수원', 'title': 'MLB키즈 MY WINTER DEBUT 팝업',
            'start': '2026-11-06', 'end': '2026-11-15', 'place': '1층', **kw}


def result(title, text, link, pub=datetime(2026, 11, 1, tzinfo=timezone.utc)):
    return {'items': [{'title': title, 'description': text, 'link': link, 'pubDate': email.utils.format_datetime(pub)}]}


class MallNewsTest(unittest.TestCase):
    def test_to_item_ok(self):
        it = mall_news.to_item(row(), ART)
        self.assertEqual((it.source, it.mall, it.url, it.start), ('mallnews', '스타필드 수원', 'https://news.example/1', date(2026, 11, 6)))
        self.assertTrue(it.id.startswith('mallnews:스타필드 수원:2026-11-06:'))
        self.assertEqual((it.place, it.brand, it.kind), ('1층', None, None))

    def test_to_item_date_not_in_article(self):
        self.assertIsNone(mall_news.to_item(row(start='2026-11-07'), ART))

    def test_to_item_unknown_mall(self):
        self.assertIsNone(mall_news.to_item(row(mall='롯데백화점 동탄'), ART))

    def test_to_item_end_before_start(self):
        self.assertIsNone(mall_news.to_item(row(end='2026-11-05'), ART))

    def test_to_item_missing_title_and_place(self):
        self.assertIsNone(mall_news.to_item(row(title=' '), ART))
        self.assertEqual(mall_news.to_item(row(place=None), ART).place, '')

    def test_to_item_end_required(self):  # 종료일이 없으면 버린다
        self.assertIsNone(mall_news.to_item(row(end=None), ART))
        self.assertIsNone(mall_news.to_item(row(end=''), ART))

    def test_to_item_end_must_be_in_article(self):  # 11월 1~3일 기사에서 end=12-31 같은 것
        art = {**ART, 'text': '11월 1일부터 3일까지 스타필드 수원 1층에서 연다'}
        self.assertIsNone(mall_news.to_item(row(start='2026-11-01', end='2026-12-31'), art))
        self.assertEqual(mall_news.to_item(row(start='2026-11-01', end='2026-11-03'), art).end, date(2026, 11, 3))

    def test_to_item_one_day_event_needs_no_second_date(self):
        art = {**ART, 'text': '11월 6일 하루 스타필드 수원 1층에서 연다'}
        self.assertEqual(mall_news.to_item(row(end='2026-11-06'), art).end, date(2026, 11, 6))

    def test_to_item_mall_evidence(self):  # 스타필드 수원만 나온 기사를 의왕으로 답해도 버린다
        self.assertIsNone(mall_news.to_item(row(mall='타임빌라스 의왕'), ART))
        art = {**ART, 'title': '롯데 프리미엄 아울렛 의왕, 키즈 팝업', 'text': '11월 6일부터 15일까지 열린다'}
        self.assertEqual(mall_news.to_item(row(mall='타임빌라스 의왕'), art).mall, '타임빌라스 의왕')
        self.assertIsNone(mall_news.to_item(row(mall='스타필드 수원'), art))

    def test_mall_evidence_rules(self):
        ev = mall_news.has_evidence
        self.assertTrue(ev('타임빌라스 의왕', '의왕 타임빌라스'))
        self.assertTrue(ev('타임빌라스 의왕', '롯데 아울렛 의왕점'))
        self.assertFalse(ev('타임빌라스 의왕', '의왕시 행사'))
        self.assertTrue(ev('타임빌라스 수원', '타임빌라스 수원'))
        self.assertFalse(ev('타임빌라스 수원', '타임빌라스 의왕'))
        self.assertTrue(ev('롯데백화점 평촌', '롯데백화점 평촌점'))
        self.assertTrue(ev('롯데몰 광교', '광교 롯데몰'))
        self.assertFalse(ev('롯데몰 광교', '광교 갤러리아'))
        self.assertTrue(ev('스타필드 수원', '스타필드 수원'))
        self.assertFalse(ev('스타필드 수원', '스타필드 하남'))
        self.assertTrue(ev('현대백화점 판교', '판교 현대백화점'))
        self.assertTrue(ev('AK플라자 수원', 'AK플라자 수원점'))
        self.assertTrue(ev('AK플라자 수원', 'ak플라자 수원'))
        self.assertFalse(ev('AK플라자 수원', 'AK플라자 분당'))

    def test_fetch_queries_and_prompt(self):
        qs = []

        def search(q):
            qs.append(q)
            return {'items': []}
        self.assertEqual(mall_news.fetch(date(2026, 11, 4), search=search, gen=lambda p: '[]'), [])
        self.assertIn('타임빌라스 의왕 팝업', qs)
        self.assertEqual(len(qs), len(mall_news.QUERY_NAMES) * 3)

    def test_fetch_filters_window_and_bad_rows(self):
        prompts = []
        res = result('MLB키즈, 스타필드 수원서 체험형 팝업', '11월 6일부터 15일까지 스타필드 수원 1층에서 연다', 'https://news.example/1')

        def gen(p):
            prompts.append(p)
            return '''[{"n":0,"mall":"스타필드 수원","title":"MLB키즈 팝업","start":"2026-11-06","end":"2026-11-15","place":"1층"},
                {"n":0,"mall":"스타필드 수원","title":"MLB키즈 팝업","start":"2026-11-06","end":"2026-11-15","place":"1층"},
                {"n":"0","mall":"스타필드 수원","title":"문자 번호","start":"2026-11-06","end":"2026-11-15"},
                {"n":5,"mall":"스타필드 수원","title":"범위 밖","start":"2026-11-06","end":"2026-11-15"},
                {"n":0,"mall":"스타필드 수원","title":"너무 먼 행사","start":"2026-11-19","end":"2026-11-20"}]'''
        out = mall_news.fetch(TODAY, search=lambda q: res, gen=gen)
        self.assertEqual([i.title for i in out], ['MLB키즈 팝업'])
        self.assertIn('2026-11-04', prompts[0])
        self.assertIn('스타필드 수원', prompts[0])
        self.assertIn('[0] 발행일 2026-11-01 | MLB키즈, 스타필드 수원서 체험형 팝업 |', prompts[0])

    def test_fetch_window_edges(self):
        rows = [('끝난 행사', '2026-11-01', '2026-11-03'), ('어제 끝', '2026-11-03', '2026-11-03'),
                ('오늘 끝', '2026-11-01', '2026-11-04'), ('14일째 시작', '2026-11-18', '2026-11-19'),
                ('15일째 시작', '2026-11-19', '2026-11-20')]
        raw = json.dumps([{'n': 0, 'mall': '스타필드 수원', 'title': t, 'start': s, 'end': e, 'place': ''} for t, s, e in rows])
        res = result('스타필드 수원 팝업', '11월 1일 11월 3일 11월 4일 11월 18일 11월 19일 11월 20일', 'https://news.example/2')
        out = mall_news.fetch(TODAY, search=lambda q: res, gen=lambda p: raw)
        self.assertEqual(sorted(i.title for i in out), ['14일째 시작', '오늘 끝'])

    def test_fetch_batch_failure_skipped(self):
        res = {'items': [dict(result(f'기사{i} 스타필드 수원 11월 6일', '11월 7일', f'https://news.example/{i}')['items'][0]) for i in range(25)]}
        calls = []

        def gen(p):
            calls.append(p)
            if len(calls) == 1:
                raise RuntimeError('boom')
            return '[{"n":0,"mall":"스타필드 수원","title":"팝업","start":"2026-11-06","end":"2026-11-07","place":""}]'
        out = mall_news.fetch(TODAY, search=lambda q: res, gen=gen)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(out), 1)

    def test_fetch_all_batches_fail_raises(self):
        res = result('팝업 11월 6일', 't', 'https://news.example/3')

        def gen(p):
            raise RuntimeError('boom')
        with self.assertRaises(RuntimeError):
            mall_news.fetch(TODAY, search=lambda q: res, gen=gen)

    def test_fetch_all_searches_fail_raises(self):
        def search(q):
            raise RuntimeError('naver down')
        with self.assertRaises(RuntimeError):
            mall_news.fetch(TODAY, search=search, gen=lambda p: '[]')

    def test_fetch_partial_search_failure_tolerated(self):
        res = result('스타필드 수원 팝업 11월 6일', '11월 7일', 'https://news.example/4')

        def search(q):
            if q.startswith('타임빌라스'):
                raise RuntimeError('x')
            return res
        out = mall_news.fetch(TODAY, search=search, gen=lambda p: '[{"n":0,"mall":"스타필드 수원","title":"팝업","start":"2026-11-06","end":"2026-11-07"}]')
        self.assertEqual(len(out), 1)


if __name__ == '__main__':
    unittest.main()
