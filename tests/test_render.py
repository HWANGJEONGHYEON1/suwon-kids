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
        self.assertIn('상시 전시·행사 1곳', out)
        self.assertIn('<details class="long">', out)
        self.assertIn('마지막 갱신 2026-10-26 05:00', out)

    def test_region_tabs(self):
        out = render.page([ev('공연', '행궁동'), ev('매직쇼', '동탄'), ev('클래식', '용인')], [], NOW)
        self.assertIn('data-r="all" aria-selected="true">전체 <span class="n">3</span>', out)
        self.assertLess(out.index('data-r="suwon"'), out.index('data-r="dongtan"'))
        self.assertLess(out.index('data-r="dongtan"'), out.index('data-r="yongin"'))
        self.assertNotIn('data-r="anyang"', out)
        self.assertIn('<section class="region" id="dongtan">', out)
        self.assertIn('[hidden]{display:none!important}', out)  # section.region 의 display:flex 가 hidden 을 덮지 않게

    def test_near_region_has_no_area_prefix(self):
        e = ev('클래식', '용인')
        e.place = '포은아트홀'
        out = render.page([e], [], NOW)
        self.assertIn('<span class="p">포은아트홀</span>', out)
        self.assertNotIn('용인 · 포은아트홀', out)

    def test_suwon_rows_show_area(self):
        e = ev('공연', '행궁동')
        e.place = '화성행궁광장'
        self.assertIn('<span class="p">행궁동 · 화성행궁광장</span>', render.page([e], [], NOW))

    def test_grouped_by_day(self):
        week = (date(2026, 10, 29), date(2026, 11, 1))
        a = ev('오늘 시작', '행궁동', date(2026, 10, 20), date(2026, 11, 1))  # 이미 시작한 여러 날 행사는 오늘에
        b = ev('토요일 공연', '행궁동', D, D)
        b.time = '14:00'
        c = ev('내일 공연', '행궁동', date(2026, 10, 30), date(2026, 10, 30))
        out = render.page([b, a, c], [], NOW, week)
        self.assertLess(out.index('오늘<span class="d">10.29</span>'), out.index('내일<span class="d">10.30</span>'))
        self.assertLess(out.index('내일<span class="d">10.30</span>'), out.index('토요일<span class="d">10.31</span>'))
        self.assertLess(out.index('>오늘 시작<'), out.index('>내일 공연<'))
        self.assertIn('<span>~11.1(일)까지</span>', out)
        self.assertIn('<span>14:00</span>', out)
        self.assertEqual(out.count('>오늘 시작<'), 1)

    def test_no_repeat_area_or_weekday(self):
        e = ev('키즈프로그램', '스타필드 수원')
        e.place, e.time = '스타필드 수원', '토 11:00·14:00'
        out = render.page([e, ev('공연', '행궁동')], [], NOW, (date(2026, 10, 29), date(2026, 11, 1)))
        self.assertIn('<span class="p">스타필드 수원</span>', out)
        self.assertIn('<span>11:00·14:00</span>', out)

    def test_sorted_by_start_time(self):
        a, b, c = ev('오후', '행궁동'), ev('오전', '행궁동'), ev('시간 모름', '행궁동')
        a.time, b.time = '14:00', '토 9:30·15:00'
        out = render.page([c, a, b], [], NOW, (date(2026, 10, 29), date(2026, 11, 1)))
        self.assertLess(out.index('>오전<'), out.index('>오후<'))
        self.assertLess(out.index('>오후<'), out.index('>시간 모름<'))

    def test_long_rows_keep_start(self):
        out = render.page([], [ev('특별전', '광교', date(2026, 10, 30), date(2026, 12, 31))], NOW, (date(2026, 10, 29), date(2026, 11, 1)))
        self.assertIn('<span>10.30(금)~12.31(목)</span>', out)

    def test_today_is_updated_without_week(self):
        out = render.page([ev('공연', '행궁동')], [], NOW)  # 갱신 10/26, 행사 10/31
        self.assertIn('토요일<span class="d">10.31</span>', out)
        self.assertNotIn('오늘<span', out)

    def test_summary_in_details(self):
        out = render.page([ev('축제', '광교', summary='불꽃 공연')], [], NOW)
        self.assertIn('<div class="more"><p class="s">불꽃 공연</p>', out)

    def test_card_details(self):
        e = ev('[경기도 공연장 상주단체 육성지원사업 UP STAGE : 경기] 콘서트 오페라', '용인')
        e.source, e.age, e.price, e.booking = 'kopis', '36개월 이상', '전석 20,000원', 'https://booking.naver.com/x'
        e.address, e.image = '경기도 용인시 수지구 문정로 15', 'https://kopis.or.kr/p.png'
        out = render.page([e], [], NOW)
        self.assertIn('<span class="t">콘서트 오페라</span>', out)
        self.assertIn('<span class="b kind">공연</span>', out)
        self.assertIn('<dt>가격</dt><dd>전석 20,000원</dd>', out)
        self.assertIn('href="https://booking.naver.com/x"', out)
        self.assertIn('https://map.naver.com/p/search/', out)
        self.assertIn('src="https://kopis.or.kr/p.png"', out)

    def test_goatcounter_and_booking_click(self):
        e = ev('매직쇼', '동탄')
        e.booking = 'https://booking.naver.com/x'
        out = render.page([e], [], NOW)
        self.assertIn('data-goatcounter="https://suwon-kids.goatcounter.com/count"', out)
        self.assertIn('data-goatcounter-click="booking" data-goatcounter-title="매직쇼">예매하기</a>', out)
        self.assertNotIn('data-goatcounter-click', render.page([ev('공연', '행궁동')], [], NOW))

    def test_goatcounter_off_when_empty(self):
        old, render.GOATCOUNTER = render.GOATCOUNTER, ''
        try:
            self.assertNotIn('goatcounter', render.page([ev('공연', '행궁동')], [], NOW))
        finally:
            render.GOATCOUNTER = old

    def test_festival_badge(self):
        out = render.page([ev('가을 축제', '행궁동')], [], NOW, festivals={'suwon:가을 축제'})
        self.assertIn('<span class="b kind">축제</span>', out)


if __name__ == '__main__':
    unittest.main()
