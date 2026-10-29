"""근교 시·뮤지엄 출처: 경기문화재단 뮤지엄, 안양 문화예술행사일정, 화성 주요 축제표, 군포 주간행사계획."""
import json
import pathlib
import unittest
from datetime import date

from suwon_kids import areas
from suwon_kids.sources import anyang, ggcf, gunpo, hwaseong

FX = pathlib.Path(__file__).parent / 'fixtures'
TODAY = date(2026, 10, 28)  # 수요일, 이번 주는 11/1(일)까지


def text(name):
    return (FX / name).read_text(encoding='utf-8')


class GgcfTest(unittest.TestCase):
    def test_parse_gcm(self):
        rows = ggcf.parse_gcm(text('ggcf_gcm_events.html'))
        self.assertEqual(len(rows), 5)
        r = rows[1]
        self.assertEqual(r['title'], '<우주댄서-행성언어> 만들기 워크숍(몸으로 소통 표현하기)')
        self.assertEqual((r['status'], r['place'], r['target'], r['price']),
                         ('진행중', '경기도어린이박물관 교육실 1', '7세~12세(5학년) 어린이', '무료'))
        self.assertTrue(r['period'].startswith('2026-10-22'))

    def test_parse_muse(self):
        rows = ggcf.parse_muse(text('ggcf_muse_events.html'))
        self.assertEqual(rows[0]['title'], '2026 경기도박물관 야간 피크닉 <달빛 아래 박물관>')
        self.assertEqual((rows[0]['place'], rows[0]['target']), ('경기도박물관 야외공간', '누구나'))

    def test_fetch_week_and_rules(self):
        pages = {'https://gcm.ggcf.kr/events?page=1': text('ggcf_gcm_events.html'),
                 'https://musenet.ggcf.kr/events?page=1': text('ggcf_muse_events.html')}
        evs = ggcf.fetch(TODAY, get=lambda url: pages.get(url, '').encode())
        titles = [e.title for e in evs]
        self.assertIn('<우주댄서-행성언어> 만들기 워크숍(몸으로 소통 표현하기)', titles)
        self.assertNotIn('2026 경기문화재단 <서클31 스탬프 투어>', titles)  # 경기도 전역
        self.assertFalse(any('종료' in t for t in titles))
        ev = next(e for e in evs if '우주댄서' in e.title)
        self.assertEqual((ev.target, ev.age, ev.price, ev.host), ('어린이', '7세~12세(5학년) 어린이', '무료', '경기도어린이박물관'))
        self.assertEqual(areas.assign(ev), '용인')

    def test_group_and_adult_dropped(self):
        row = {'url': 'https://gcm.ggcf.kr/edus/1', 'title': '[단체] 동화구연', 'status': '진행중',
               'period': '2026-10-01(목) ~ 2026-11-01(일)', 'place': '교육실', 'target': '영유아 단체', 'price': None}
        self.assertIsNone(ggcf.to_event(row, '경기도어린이박물관'))
        self.assertIsNone(ggcf.to_event({**row, 'title': '특강', 'target': '청소년 이상 누구나'}, '경기도박물관'))
        self.assertIsNotNone(ggcf.to_event({**row, 'title': '특강', 'target': '누구나'}, '경기도박물관'))

    def test_offsite_dropped(self):
        row = {'url': 'https://musenet.ggcf.kr/events/1', 'title': '토크 콘서트', 'status': '', 'target': '누구나', 'price': None,
               'period': '2026-10-31(토) ~ 2026-10-31(토)', 'place': '경기도서관 지하 1층 플래닛 경기홀'}
        self.assertIsNone(ggcf.to_event(row, '경기도박물관'))
        self.assertIsNotNone(ggcf.to_event({**row, 'place': '경기도박물관 야외공간'}, '경기도박물관'))
        self.assertIsNotNone(ggcf.to_event({**row, 'place': '3층《우리는 지구별 친구들》전시실'}, '경기도박물관'))


class AnyangTest(unittest.TestCase):
    def test_calendar_days(self):
        cal = anyang.parse_calendar(text('anyang_cal.html'), 2026, 10)
        self.assertEqual(cal['2791'], {'title': '병목안 축제', 'days': [date(2026, 10, 31)]})

    def test_fetch(self):
        def get(url):
            if 'selectSchdulWebList' in url:
                return text('anyang_cal.html').encode() if 'searchMonth=10' in url else b''
            return text('anyang_view.html').encode()
        evs = anyang.fetch(TODAY, get=get)
        self.assertEqual([(e.title, e.start, e.place) for e in evs], [('병목안 축제', date(2026, 10, 31), '병목안공원')])
        self.assertEqual(areas.assign(evs[0]), '안양')

    def test_outreach_skipped(self):
        evs = anyang.fetch(date(2026, 10, 1), get=lambda url: (text('anyang_cal.html') if 'searchMonth=10' in url else
                                                               text('anyang_view.html') if 'View' in url else '').encode())
        self.assertFalse(any(e.title.startswith('찾아가는') for e in evs))

    def test_week_across_months(self):
        self.assertEqual(anyang._months((date(2026, 10, 29), date(2026, 11, 1))), [(2026, 10), (2026, 11)])


class HwaseongTest(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(hwaseong.dates('10. 31.(토)', 2026), (date(2026, 10, 31), date(2026, 10, 31)))
        self.assertEqual(hwaseong.dates('5. 22.(금) ~ 25.(월)', 2026), (date(2026, 5, 22), date(2026, 5, 25)))
        self.assertEqual(hwaseong.dates('10. 30.(금)~10. 31.(토)', 2026), (date(2026, 10, 30), date(2026, 10, 31)))
        self.assertIsNone(hwaseong.dates('하반기(10월 말 예정)', 2026))

    def test_fetch_week_and_dongtan(self):
        evs = hwaseong.fetch(TODAY, get=lambda url: text('hwaseong.html').encode())
        self.assertEqual({e.title for e in evs}, {'화성 루나빛축제', '화성시 평생학습축제'})
        luna = next(e for e in evs if '루나빛' in e.title)
        self.assertEqual(luna.address, '경기도 화성시 동탄구 동탄호수공원')
        self.assertEqual(areas.assign(luna), '동탄')

    def test_no_double_city(self):
        evs = hwaseong.parse(text('hwaseong.html'))
        boat = next(e for e in evs if '뱃놀이' in e.title)
        self.assertNotIn('화성시 화성시', boat.address)


class GunpoTest(unittest.TestCase):
    def test_posts(self):
        p = gunpo.posts(text('gunpo_list.html'))
        self.assertEqual(p[0][1], date(2026, 10, 26))
        self.assertIn('nttNo=328358', p[0][0])

    def test_rows_aligned(self):
        rows = gunpo.rows((FX / 'gunpo_week.hwpx').read_bytes(), date(2026, 10, 26))
        walk = next(r for r in rows if '치매극복' in r['title'])
        self.assertEqual((walk['date'], walk['time'], walk['place']), (date(2026, 10, 29), '09:30', '당정근린공원'))

    def test_fetch_uses_pick(self):
        def get(url):
            if 'selectBbsNttList' in url:
                return text('gunpo_list.html').encode()
            if 'selectBbsNttView' in url:
                return text('gunpo_view.html').encode()
            return (FX / 'gunpo_week.hwpx').read_bytes()
        seen = []

        def gen(prompt):
            seen.append(prompt)
            items = [line for line in prompt.splitlines() if line[:1].isdigit()]
            return json.dumps([int(line.split('.')[0]) for line in items if '걷기' in line or '반려동물' in line])
        evs = gunpo.fetch(TODAY, get=get, gen=gen)
        self.assertEqual([e.title for e in evs], ['2026년 한마음 치매극복 걷기행사', '2026년 반려동물 문화교실(오전)',
                                                  '2026년 반려동물 문화교실(오후)'])
        self.assertNotIn('10/26', seen[0])  # 지난 날(월·화)은 고르기 전에 뺀다
        self.assertNotIn('힐링교육(1차)', seen[0])
        self.assertEqual(areas.assign(evs[0]), '군포')

    def test_new_year_rollover(self):
        import io
        import zipfile
        buf = io.BytesIO()
        cell = lambda *ps: '<hp:tc>' + ''.join(f'<hp:p><hp:t>{p}</hp:t></hp:p>' for p in ps) + '</hp:tc>'
        tr = lambda d: '<hp:tr>' + cell(d, '(목)') + cell('10:00') + cell('○') + cell('해맞이') + cell('수리산') + '</hp:tr>'
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('Contents/section0.xml', tr('12/31') + tr('1/1'))
        self.assertEqual([r['date'] for r in gunpo.rows(buf.getvalue(), date(2026, 12, 28))],
                         [date(2026, 12, 31), date(2027, 1, 1)])

    def test_pick_falls_back_to_rules(self):
        from suwon_kids import ai

        def down(prompt):
            raise ai.AIError('HTTP 429')
        items = [{'title': '2026년 민원공무원 힐링교육(2차)', 'place': '강원도 홍천'},
                 {'title': '2026년 한마음 치매극복 걷기행사', 'place': '당정근린공원'},
                 {'title': '제9기 지역보건의료계획 수립단 회의', 'place': '중회의실'},
                 {'title': '작은도서관 운영자 워크숍', 'place': '충북 청주시'},
                 {'title': '2026년 반려동물 문화교실(오전)', 'place': '다목적운동장'}]
        self.assertEqual([it['title'] for it in gunpo.pick(items, gen=down)],
                         ['2026년 한마음 치매극복 걷기행사', '2026년 반려동물 문화교실(오전)'])

    def test_pick_ignores_bad_numbers(self):
        items = [{'title': 'a', 'place': None}, {'title': 'b', 'place': 'x'}]
        self.assertEqual(gunpo.pick(items, gen=lambda p: '[1, 7, -1, 1]'), [items[1]])
        self.assertEqual(gunpo.pick(items, gen=lambda p: '없음'), [])


if __name__ == '__main__':
    unittest.main()
