"""화성시 문화관광 '주요 축제·행사 일정' 표 (한 해 10건 안팎). 날짜는 '10. 31.(토)', '5. 22.(금) ~ 25.(월)',
'10. 30.(금)~10. 31.(토)' 꼴이고, '하반기(10월 말 예정)'처럼 날짜가 안 정해진 행은 뺀다. 연도는 표 제목에서 읽는다."""
import html
import re
from datetime import date

from suwon_kids import http, week
from suwon_kids.models import Event

URL = 'https://tour.hscity.go.kr/NEW/6festival/festival5.jsp'
START = re.compile(r'^\s*(\d{1,2})\.\s*(\d{1,2})\.')
END = re.compile(r'~\s*(?:(\d{1,2})\.\s*)?(\d{1,2})\.')


def _text(s: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def dates(raw: str, year: int) -> tuple[date, date] | None:
    m = START.match(raw)
    if not m:
        return None
    start = date(year, int(m.group(1)), int(m.group(2)))
    e = END.search(raw)
    end = date(year, int(e.group(1) or start.month), int(e.group(2))) if e else start
    return (start, end) if end >= start else None


def parse(page: str) -> list[Event]:
    y = re.search(r'(\d{4})년 화성시 주요 축제', page)
    if not y:
        return []
    out = []
    for row in re.findall(r'<tr>\s*(<td>.*?)</tr>', page, re.S):
        cells = [_text(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)]
        if len(cells) < 6:
            continue
        no, when, title, _dept, place, host = cells[:6]
        span = dates(when, int(y.group(1)))
        if not span:
            continue
        # 동탄에서 열리면 동탄 탭으로 가게 주소에 동탄구를 넣는다
        city = '경기도 화성시 동탄구' if '동탄' in place else '경기도 화성시'
        out.append(Event(
            id=f'hwaseong:{span[0]}:{re.sub(r"[^0-9A-Za-z가-힣]", "", title)}', source='hwaseong', title=title,
            start=span[0], end=span[1], time=None, place=place, address=f"{city} {re.sub(r'^화성시\s*', '', place)}", url=URL,
            target='누구나', host=host or '화성시'))
    return out


def fetch(today: date | None = None, get=http.get) -> list[Event]:
    rng = week.this_week(today or date.today())
    return [e for e in parse(get(URL).decode('utf-8', 'replace')) if week.overlaps(e, rng)]
