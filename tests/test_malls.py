import contextlib
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from suwon_kids import malls
from suwon_kids.models import MallItem


def item(title, brand=None, place='', mall='타임빌라스 의왕', start=date(2026, 11, 1), end=date(2026, 11, 8), source='lotte', id=None):
    return MallItem(id or f'{source}:{title}', source, mall, title, brand, start, end, place, 'https://x')


class MallsTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.tmp = Path(d.name)

    def test_rule(self):
        self.assertTrue(malls.rule(item('가을 피크닉 Pop-Up', '텔레토비')))
        self.assertTrue(malls.rule(item('Winter Early Bird', '나이키키즈')))
        self.assertTrue(malls.rule(item('인기상품 균일가전', '네파키즈', '6F 아동행사장')))
        self.assertTrue(malls.rule(item('곤충ㆍ파충류 POP-UP STORE')))
        self.assertFalse(malls.rule(item('카드사별 무이자 할부 혜택', '카드혜택')))
        self.assertFalse(malls.rule(item('스팀 세차장')))
        # 어른 브랜드·식품·영화관·귀금속은 규칙에서 바로 뺀다 (2026-11-04 실제 목록)
        self.assertFalse(malls.rule(item('특별 할인 이벤트!!', '롯데시네마 광교점')))
        self.assertFalse(malls.rule(item('푸드 트레일러 Pop-Up', '쉐이크쉑')))
        self.assertFalse(malls.rule(item('미국식 와일드 그릴 핫도그', '와그독')))
        self.assertFalse(malls.rule(item('[타코빽] 타코야끼 POP-UP')))
        self.assertFalse(malls.rule(item('자연방사 유정란', 'OGG')))
        self.assertFalse(malls.rule(item('24K 돌반지 컬렉션', '골든듀')))
        self.assertFalse(malls.rule(item('K2그룹전 [아이더] 슈퍼위크')))
        self.assertIsNone(malls.rule(item('[POP-UP STORE] 리틀티니', place='5층 캐리마켓 옆')))

    def test_kind(self):
        self.assertEqual(malls.kind_of(item('가을 피크닉 Pop-Up', '텔레토비')), 'play')
        self.assertEqual(malls.kind_of(item('Winter Early Bird', '나이키키즈')), 'shop')

    def test_classify_uses_gemini_once_and_caches(self):
        asked = []

        def gen(p):
            asked.append(p)
            return '[{"n": 0, "kid": true, "kind": "shop"}]'
        cache = {}
        x = item('[POP-UP STORE] 리틀티니', source='hyundai', id='hyundai:E1')
        self.assertEqual([i.kind for i in malls.classify([x], cache, gen)], ['shop'])
        malls.classify([x], cache, gen)
        self.assertEqual(len(asked), 1)
        self.assertEqual(cache['hyundai:E1'], {'kid': True, 'kind': 'shop'})

    def test_classify_failure_not_cached(self):
        def gen(p):
            raise RuntimeError('quota')
        cache = {}
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(malls.classify([item('[POP-UP STORE] 미니도우', id='h:2')], cache, gen), [])
        self.assertEqual(cache, {})

    def test_merge_prefers_official(self):
        a = item('MLB키즈 MY WINTER DEBUT 팝업', mall='스타필드 수원', source='mallnews', id='mallnews:1', start=date(2026, 11, 6), end=date(2026, 11, 15))
        b = item('MY WINTER DEBUT', 'MLB키즈', mall='스타필드 수원', source='starfield', id='sf:1', start=date(2026, 11, 5), end=date(2026, 11, 20))
        self.assertEqual([i.id for i in malls.merge([a, b])], ['sf:1'])

    def test_merge_keeps_different_malls(self):
        a = item('캐릭터 Pop-Up', '52토이즈', mall='타임빌라스 수원', id='a')
        b = item('캐릭터 Pop-Up', '52토이즈', mall='롯데백화점 평촌', id='b')
        self.assertEqual(len(malls.merge([a, b])), 2)

    def test_merge_common_word_not_enough(self):
        a = item('헬로키티 팝업', source='mallnews', id='mallnews:2')
        b = item('[52토이즈] 캐릭터 Pop-Up', source='lotte', id='lotte:2')
        self.assertEqual(sorted(i.id for i in malls.merge([a, b])), ['lotte:2', 'mallnews:2'])
        c = item('캐릭터 Pop-Up 팝업 오픈', source='mallnews', id='mallnews:3')  # '캐릭터'만 겹치면 같은 행사로 본다
        self.assertEqual([i.id for i in malls.merge([c, b])], ['lotte:2'])

    def test_collect_window_counts_errors(self):
        today = date(2026, 11, 4)
        srcs = {'lotte': lambda t: [item('가을 피크닉 Pop-Up', '텔레토비'),
                                    item('지난 팝업 키즈', end=date(2026, 11, 3)),
                                    item('먼 팝업 키즈', start=date(2026, 11, 19), end=date(2026, 11, 30))],
                'ak': lambda t: (_ for _ in ()).throw(RuntimeError('down'))}
        items, counts, errors = malls.collect(today, srcs, gen=lambda p: '[]', cache_path=self.tmp / 'c.json')
        self.assertEqual([i.brand for i in items], ['텔레토비'])
        self.assertEqual(counts, {'lotte': 3})
        self.assertIn('RuntimeError: down', errors['ak'])

    def test_collect_saves_cache(self):
        x = item('[POP-UP STORE] 리틀티니', source='hyundai', id='hyundai:E1')
        path = self.tmp / 'state' / 'c.json'
        malls.collect(date(2026, 11, 4), {'hyundai': lambda t: [x]}, gen=lambda p: '[{"n": 0, "kid": false}]', cache_path=path)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'hyundai:E1': {'kid': False, 'kind': None}})

    def test_to_event_and_write(self):
        it = item('가을 피크닉 Pop-Up', '텔레토비', '잔디광장')
        it.kind = 'play'
        ev = malls.to_event(it)
        self.assertEqual((ev.area, ev.place, ev.title, ev.address), ('백화점', '타임빌라스 의왕 · 잔디광장', '[텔레토비] 가을 피크닉 Pop-Up', '경기도 의왕시 바라산로 1'))
        self.assertEqual(malls.to_event(item('x')).place, '타임빌라스 의왕')
        p = self.tmp / 'malls.json'
        self.assertEqual(malls.write([it], date(2026, 11, 4), p), 1)
        d = json.loads(p.read_text(encoding='utf-8'))
        self.assertEqual(d['updated'], '2026-11-04')
        self.assertEqual(d['malls'][0]['kind'], 'play')
        self.assertEqual(d['malls'][0]['address'], '경기도 의왕시 바라산로 1')


if __name__ == '__main__':
    unittest.main()
