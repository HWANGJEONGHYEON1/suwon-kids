import unittest
from datetime import date

from suwon_kids import areas, dedupe
from suwon_kids.models import Event

D = date(2026, 10, 31)


def ev(place='', address='', title='t', source='suwon', start=D, end=D):
    return Event(f'{source}:{title}:{start}', source, title, start, end, None, place, address, '', '누구나')


class AreaTest(unittest.TestCase):
    def test_area_starfield(self):
        self.assertEqual(areas.assign(ev('대유평공원 및 111CM 야외 일원')), '스타필드 수원')

    def test_area_haenggung(self):
        self.assertEqual(areas.assign(ev('화성행궁광장')), '행궁동')

    def test_area_gwanggyo(self):
        self.assertEqual(areas.assign(ev('광교호수공원')), '광교')

    def test_area_gu_fallback(self):
        self.assertEqual(areas.assign(ev('다래기장터', '경기도 수원시 권선구 당수로 130')), '권선구')

    def test_area_other(self):
        self.assertEqual(areas.assign(ev('온라인')), '기타')


class DedupeTest(unittest.TestCase):
    def test_dedupe_same_title_overlap(self):
        a = ev(title='2026 가을 키즈 페스타', source='starfield')
        b = ev(title='가을 키즈 페스타 (2026)', source='suwon')
        out = dedupe.merge([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].source, 'suwon')

    def test_dedupe_keeps_different_dates(self):
        a = ev(title='키즈 프로그램', start=date(2026, 10, 31), end=date(2026, 10, 31))
        b = ev(title='키즈 프로그램', start=date(2026, 11, 7), end=date(2026, 11, 7))
        self.assertEqual(len(dedupe.merge([a, b])), 2)


if __name__ == '__main__':
    unittest.main()
