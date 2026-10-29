import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from suwon_kids import build
from suwon_kids.models import Event

TODAY = date(2026, 10, 26)


def ev(title, source='suwon', start=date(2026, 10, 31), end=date(2026, 10, 31), target='누구나', place='화성행궁광장', image=None):
    return Event(f'{source}:{title}', source, title, start, end, None, place, '', 'https://x', target, image=image)


def fail():
    raise RuntimeError('down')


def detail(seq):
    return {'host': '수원특례시', 'body': f'{seq} 안내문 가수 공연'}


def gen(prompt, image_url=None):
    return '가수 공연'


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.cache = self.dir / 'posters.json'

    def run_build(self, sources):
        return build.run(TODAY, self.dir, sources, detail=detail, gen=gen, poster_cache=self.cache)

    def test_all_sources_fail_keeps_old(self):
        (self.dir / 'events.json').write_text('X')
        r = self.run_build({'suwon': fail, 'starfield': fail})
        self.assertFalse(r['ok'])
        self.assertEqual((self.dir / 'events.json').read_text(), 'X')
        self.assertFalse((self.dir / 'index.html').exists())

    def test_zero_events_keeps_old(self):
        (self.dir / 'events.json').write_text('X')
        r = self.run_build({'suwon': lambda: [ev('지난 행사', start=date(2026, 9, 1), end=date(2026, 9, 2))]})
        self.assertFalse(r['ok'])
        self.assertEqual((self.dir / 'events.json').read_text(), 'X')

    def test_one_source_fails_others_written(self):
        r = self.run_build({'suwon': lambda: [ev('가을 공연')], 'starfield': fail})
        self.assertTrue(r['ok'])
        self.assertIn('starfield', r['errors'])
        data = json.loads((self.dir / 'events.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['events']), 1)

    def test_events_json_shape(self):
        self.run_build({'suwon': lambda: [ev('가을 공연'), ev('상설전', start=date(2026, 1, 1), end=date(2026, 12, 31))]})
        data = json.loads((self.dir / 'events.json').read_text(encoding='utf-8'))
        self.assertEqual(set(data), {'updated', 'week', 'events', 'long'})
        self.assertEqual(data['week'], ['2026-10-26', '2026-11-01'])
        e = data['events'][0]
        for k in ('title', 'start', 'end', 'area', 'url', 'summary', 'host', 'festival'):
            self.assertIn(k, e)
        self.assertEqual(e['area'], '행궁동')
        self.assertEqual(e['summary'], '가수 공연')
        self.assertEqual([x['title'] for x in data['long']], ['상설전'])

    def test_adult_dropped_festival_kept(self):
        self.run_build({'suwon': lambda: [ev('성인 강연', target='성인'), ev('통닭거리 축제', target='성인')]})
        data = json.loads((self.dir / 'events.json').read_text(encoding='utf-8'))
        self.assertEqual([x['title'] for x in data['events']], ['통닭거리 축제'])
        self.assertTrue(data['events'][0]['festival'])

    def test_starfield_poster_summary(self):
        poster = {'programs': [{'name': '쿠키 만들기', 'date': '10.31', 'time': '14:00', 'age': '5~7세'},
                               {'name': '종이접기', 'date': '11.7', 'time': '', 'age': ''}]}
        self.cache.write_text(json.dumps({'https://img/1.jpg': poster}, ensure_ascii=False))
        self.run_build({'starfield': lambda: [ev('키즈프로그램', 'starfield', place='스타필드 수원', image='https://img/1.jpg')]})
        data = json.loads((self.dir / 'events.json').read_text(encoding='utf-8'))
        self.assertEqual(data['events'][0]['summary'], '쿠키 만들기 14:00 (5~7세)')


class PosterLineTest(unittest.TestCase):
    def test_korean_date_format(self):
        poster = {'programs': [{'name': '읽고 쓰는 삶', 'date': '10월 31일(토)', 'time': '', 'age': ''},
                               {'name': '다른 날', 'date': '10월 3일(토)', 'time': '', 'age': ''}]}
        self.assertEqual(build._poster_line(ev('x'), poster), '읽고 쓰는 삶')

    def test_poster_extra_adds_time_venue_price(self):
        e = ev('x', start=date(2026, 10, 31), end=date(2026, 10, 31))
        e.place = '스타필드 수원'
        poster = {'programs': [{'name': '비눗방울맨', 'date': '10.31(토)', 'time': '', 'age': ''}],
                  'time': '오후 2시/5시', 'venue': '3F 별마당 키즈', 'price': '무료'}
        build._poster_extra(e, poster)
        self.assertEqual((e.time, e.place, e.price), ('오후 2시/5시', '스타필드 수원 3F 별마당 키즈', '무료'))

    def test_poster_extra_prefers_that_days_program_time(self):
        e = ev('x', start=date(2026, 10, 28), end=date(2026, 10, 28))
        e.place = '스타필드 수원'
        poster = {'programs': [{'name': '읽고 쓰는 삶', 'date': '10월 28일(수)', 'time': '오후 2시', 'age': ''}],
                  'time': '', 'venue': '', 'price': ''}
        build._poster_extra(e, poster)
        self.assertEqual((e.time, e.place, e.price), ('오후 2시', '스타필드 수원', None))

    def test_no_prefix_collision(self):
        poster = {'programs': [{'name': '그믐날', 'date': '10.31(토)', 'time': '', 'age': ''}]}
        self.assertIsNone(build._poster_line(ev('x', start=date(2026, 10, 3), end=date(2026, 10, 3)), poster))


if __name__ == '__main__':
    unittest.main()


class ReviewFixBuildTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_poster_fetch_error_does_not_crash(self):
        import urllib.error

        def bad_gen(prompt, image_url=None):
            raise urllib.error.URLError('reset')
        r = build.run(TODAY, self.dir, {'starfield': lambda: [ev('키즈', 'starfield', image='https://img/x.jpg')]},
                      detail=detail, gen=bad_gen, poster_cache=self.dir / 'p.json')
        self.assertTrue(r['ok'])

    def test_detail_failure_keeps_festival(self):
        def bad_detail(seq):
            raise OSError('down')
        r = build.run(TODAY, self.dir, {'suwon': lambda: [ev('통닭거리 축제', target='성인')]},
                      detail=bad_detail, gen=gen, poster_cache=self.dir / 'p.json')
        data = json.loads((self.dir / 'events.json').read_text(encoding='utf-8'))
        self.assertEqual([x['title'] for x in data['events']], ['통닭거리 축제'])
        self.assertIn('detail', r['errors'])
