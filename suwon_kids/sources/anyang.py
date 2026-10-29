"""안양시 문화예술행사일정 (시 축제·음악회 달력). 날짜는 달력 칸에만 있어서 월 달력에서 날짜를 모으고,
장소·연령·입장료는 행사 상세에서 읽는다. 여러 날 행사는 칸마다 나오므로 첫날~마지막날로 묶는다."""
import html
import re
from datetime import date

from suwon_kids import http, week
from suwon_kids.models import Event

BASE = 'https://www.anyang.go.kr/main/'
CAL = BASE + 'selectSchdulWebList.do?key=1482&searchYear={y}&searchMonth={m}'
VIEW = BASE + 'selectSchdulWebView.do?key=1482&schdulNo={no}'
DAY = re.compile(r'p-calendar-list__day">\s*<span>(\d+)</span>(.*?)(?=p-calendar-list__day|</tbody>)', re.S)
ITEM = re.compile(r'schdulNo=(\d+)[^>]*>.*?title="([^"]+)"', re.S)
OUTREACH = '찾아가는'  # 학교·교회로 찾아가는 공연은 일반 가족이 갈 수 없다


def _text(s: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<br\s*/?>|<[^>]+>', ' ', s))).strip()


def parse_calendar(page: str, year: int, month: int) -> dict[str, dict]:
    """{schdulNo: {'title', 'days': [date, ...]}}"""
    out = {}
    for day, cell in DAY.findall(page):
        for no, title in ITEM.findall(cell):
            ev = out.setdefault(no, {'title': html.unescape(title).strip(), 'days': []})
            ev['days'].append(date(year, month, int(day)))
    return out


def parse_view(page: str) -> dict:
    """상세 표: 2차 구분, 행사내용, 장소, 관람연령, 입장료."""
    return {_text(k): _text(v) for k, v in re.findall(r'<th scope="row">(.*?)</th>\s*<td>(.*?)</td>', page, re.S)}


def _months(rng: tuple[date, date]) -> list[tuple[int, int]]:
    return sorted({(rng[0].year, rng[0].month), (rng[1].year, rng[1].month)})


def _get(url: str) -> bytes:
    return http.get(url, legacy_tls=True)


def fetch(today: date | None = None, get=_get) -> list[Event]:
    rng = week.this_week(today or date.today())
    found: dict[str, dict] = {}
    for y, m in _months(rng):
        for no, ev in parse_calendar(get(CAL.format(y=y, m=m)).decode('utf-8', 'replace'), y, m).items():
            found.setdefault(no, {'title': ev['title'], 'days': []})['days'] += ev['days']
    out = []
    for no, ev in found.items():
        start, end = min(ev['days']), max(ev['days'])
        if not (start <= rng[1] and end >= rng[0]) or ev['title'].startswith(OUTREACH):
            continue
        try:
            d = parse_view(get(VIEW.format(no=no)).decode('utf-8', 'replace'))
        except Exception:
            d = {}
        place = d.get('장소') or '안양시'
        out.append(Event(
            id=f'anyang:{no}', source='anyang', title=ev['title'], start=start, end=end, time=None,
            place=place, address=f'경기도 안양시 {place}', url=VIEW.format(no=no), target='누구나', host='안양시',
            age=d.get('관람연령') or None, price=d.get('입장료') or None))
    return out
