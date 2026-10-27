import unittest
from datetime import date, datetime

from suwon_kids import render
from suwon_kids.models import Event

D = date(2026, 10, 31)
NOW = datetime(2026, 10, 26, 5, 0)


def ev(title, area, start=D, end=D, summary=None):
    return Event(f'suwon:{title}', 'suwon', title, start, end, None, '', '', 'https://x/1', '누구나', area=area, summary=summary)


class RenderTest(unittest.TestCase):
    def test_escapes_brackets(self):
        out = render.page([ev('테마전시 <고문서로 만나는 조선의 일상>', '행궁동')], [], NOW)
        self.assertIn('&lt;고문서', out)
        self.assertNotIn('<고문서', out)

    def test_empty_area_hidden(self):
        out = render.page([ev('공연', '행궁동')], [], NOW)
        self.assertNotIn('>광교<', out)

    def test_area_order(self):
        out = render.page([ev('a', '행궁동'), ev('b', '스타필드 수원')], [], NOW)
        self.assertLess(out.index('>스타필드 수원<'), out.index('>행궁동<'))

    def test_home_screen_links(self):
        out = render.page([ev('공연', '행궁동')], [], NOW)
        self.assertIn('<link rel="manifest" href="manifest.webmanifest">', out)
        self.assertIn('<link rel="apple-touch-icon" href="apple-touch-icon.png">', out)
        self.assertIn('<meta name="apple-mobile-web-app-title" content="수원 아이랑">', out)

    def test_no_tags(self):
        out = render.page([ev('공연', '행궁동')], [], NOW)
        self.assertNotIn('유모차', out)
        self.assertNotIn('주차', out)

    def test_title_and_date_format(self):
        out = render.page([ev('축제', '광교', date(2026, 10, 30), date(2026, 11, 1), '불꽃 공연')], [], NOW)
        self.assertIn('이번 주 수원·근교, 애랑 갈 만한 곳', out)
        self.assertIn('출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)', out)
        self.assertIn('10.30(금)~11.1(일)', out)
        self.assertIn('불꽃 공연', out)
        self.assertIn('href="https://x/1"', out)

    def test_long_section_and_updated(self):
        out = render.page([], [ev('상설전', '광교', date(2026, 1, 1), date(2026, 12, 31))], NOW)
        self.assertIn('상시 전시·행사', out)
        self.assertIn('마지막 갱신 2026-10-26 05:00', out)


if __name__ == '__main__':
    unittest.main()
