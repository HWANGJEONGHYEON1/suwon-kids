"""경기아트센터 공연·전시 일정 (수원 인계동 대극장·소극장만).
목록은 POST /ajax/ggac/schedule/template.do (날짜는 YYYY-MM-DD) 가 HTML 조각으로 준다.
경기문화재단은 1차에서 뺐다 (설계 7-1, 계획 Task 8)."""
import html
import re
import urllib.parse
from datetime import date

from suwon_kids import http, week
from suwon_kids.models import Event

SITE = 'https://www.ggac.or.kr'
LIST = f'{SITE}/ajax/ggac/schedule/template.do'
SUWON_HALLS = ('대극장', '소극장')
ADDRESS = '경기도 수원시 팔달구 효원로 307'

ITEM = re.compile(r'<p class="txt">\s*<a href="view\.do\?idx=(\w+)">\s*<strong>(.*?)</strong>\s*'
                  r'<span class="date">\s*(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})\s*</span>\s*'
                  r'<span class="place">(.*?)</span>', re.S)


def last_page(page: str) -> int:
    return max([int(n) for n in re.findall(r'fn_linkPage\((\d+)\)', page)] or [1])


def parse_ggac(page: str) -> list[Event]:
    out = []
    for idx, title, s, e, place in ITEM.findall(page):
        place = html.unescape(place).strip()
        hall = next((h for h in SUWON_HALLS if h in place), None)
        if not hall:
            continue
        out.append(Event(
            id=f'ggac:{idx}', source='ggac', title=html.unescape(title).strip(),
            start=date.fromisoformat(s), end=date.fromisoformat(e), time=None,
            place=f'경기아트센터 {hall}', address=ADDRESS,
            url=f'{SITE}/ggac/M0000155/show/view.do?idx={idx}', target='누구나', host='경기아트센터'))
    return out


def _page(rng: tuple[date, date], n: int) -> str:
    data = urllib.parse.urlencode({'searchLocPerform': 'CD001044', 'pageIndex': n,
                                   'searchSdate': rng[0].isoformat(), 'searchEdate': rng[1].isoformat()}).encode()
    return http.post(LIST, data).decode('utf-8', 'replace')


def fetch_ggac(today: date | None = None) -> list[Event]:
    rng = week.this_week(today or date.today())
    first = _page(rng, 1)
    pages = [first] + [_page(rng, n) for n in range(2, min(last_page(first), 10) + 1)]
    return [e for p in pages for e in parse_ggac(p)]
