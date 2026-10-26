import pathlib
import unittest
from datetime import date

from suwon_kids import filters
from suwon_kids.models import Event
from suwon_kids.sources import suwon_portal

D = date(2026, 10, 31)


def ev(title, target, host=None):
    return Event('x', 'suwon', title, D, D, None, '', '', '', target, host=host)


class DetailTest(unittest.TestCase):
    def test_parse_detail_host(self):
        html = (pathlib.Path(__file__).parent / 'fixtures/portal_detail.html').read_text(encoding='utf-8')
        d = suwon_portal.parse_detail(html)
        self.assertIn('수원', d['host'])
        self.assertIn('개막식', d['body'])
        self.assertNotIn('<br', d['body'])


class FilterTest(unittest.TestCase):
    def test_keep_everyone(self):
        self.assertTrue(filters.keep(ev('가을 음악회', '누구나')))

    def test_keep_children(self):
        self.assertTrue(filters.keep(ev('인형극', '어린이 / 청소년')))

    def test_keep_adult_only_dropped(self):
        self.assertFalse(filters.keep(ev('가을 음악회', '성인')))

    def test_keep_recruit_dropped(self):
        self.assertFalse(filters.keep(ev('아나바다 장터 참가자 모집', '누구나')))

    def test_host_exception(self):
        self.assertTrue(filters.keep(ev('2026 수원 통닭거리 축제', '성인', '수원특례시')))

    def test_host_exception_gyeonggi(self):
        self.assertTrue(filters.is_host_exception('경기 가을 페스타', '경기문화재단'))

    def test_host_exception_needs_festival_word(self):
        self.assertFalse(filters.keep(ev('시민 강좌', '성인', '수원특례시')))

    def test_host_exception_needs_host(self):
        self.assertFalse(filters.is_host_exception('민간 축제', '○○기획'))
        self.assertFalse(filters.is_host_exception('민간 축제', None))


if __name__ == '__main__':
    unittest.main()
