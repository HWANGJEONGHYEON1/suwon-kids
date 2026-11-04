"""스타필드 수원 이벤트. 이벤트 페이지에서 쿠키를 먼저 받아야 목록 API가 데이터를 준다 (쿠키 없으면 data: [])."""
import json
import re
from datetime import date, datetime

from suwon_kids import http
from suwon_kids.models import Event, MallItem

SITE = 'https://www.starfield.co.kr'
PAGE = f'{SITE}/suwon/eventBenefit/events'
API = f'{SITE}/api/suwon/event/eventList.do?evt_gbn=event&lang=ko&pageIndex=1'
BRAND_PAGE = f'{SITE}/suwon/eventBenefit/brand'
BRAND_API = f'{SITE}/api/suwon/event/eventList.do?evt_gbn=brand&lang=ko&isPromotionShop=true&pageIndex='
BRAND_MAX_PAGES = 3


def fetch() -> list[dict]:
    jar = http.new_jar()
    http.get(PAGE, jar=jar)
    d = json.loads(http.get(API, {'Referer': PAGE, 'X-Requested-With': 'XMLHttpRequest'}, jar=jar))
    if not d.get('data'):
        raise RuntimeError('starfield empty')
    return d['data']


def parse_dates(txt: str, posted: date) -> list[date]:
    out = []
    for m, d in re.findall(r'(\d{1,2})\.(\d{1,2})\s*\(', txt or ''):
        m, d = int(m), int(d)
        year = posted.year + 1 if m <= posted.month - 3 else posted.year
        out.append(date(year, m, d))
    return out


def _day(s: str) -> date:
    return datetime.strptime(s[:10], '%Y-%m-%d').date()


def to_events(row: dict) -> list[Event]:
    title = re.sub(r'\s+', ' ', re.sub(r'<br\s*/?>', ' ', row.get('evt_titl') or '', flags=re.I)).strip()
    posted, until = _day(row['evt_post_strt_dt']), _day(row['evt_post_end_dt'])
    days = parse_dates(row.get('evtStrtDtTxt'), posted)
    spans = [(d, d) for d in days] or [(posted, until)]
    return [Event(
        id=f"starfield:{row['evt_seq']}:{s:%Y%m%d}",
        source='starfield',
        title=title,
        start=s,
        end=e,
        time=None,
        place='스타필드 수원',
        address='경기도 수원시 장안구 수성로 175',
        url=PAGE,
        target='누구나',
        image=SITE + row['img_uri'] if row.get('img_uri') else None,
    ) for s, e in spans]


def _title(raw: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<br\s*/?>', ' ', raw or '', flags=re.I)).strip()


def _dot_day(s: str) -> date:
    return datetime.strptime(s[:10], '%Y.%m.%d').date()


def brand_items(rows: list[dict]) -> list[MallItem]:
    """브랜드 행사 목록. 끝이 2900년 이후인 상시 안내(2017.01.01 ~ 2999.12.31)는 버린다."""
    out = []
    for row in rows:
        try:
            start, end = _dot_day(row['evt_strt_dt']), _dot_day(row['evt_end_dt'])
        except (KeyError, TypeError, ValueError):
            continue
        title = _title(row.get('evt_titl'))
        if end.year >= 2900 or not (row.get('evt_seq') and title):
            continue
        out.append(MallItem(
            id=f"starfield-brand:{row['evt_seq']}",
            source='starfield',
            mall='스타필드 수원',
            title=title,
            brand=None,
            start=start,
            end=end,
            place='',
            url=f"{BRAND_PAGE}/{row['evt_seq']}",
        ))
    return out


def fetch_brand(today: date, get=http.get) -> list[MallItem]:
    jar = http.new_jar()
    get(BRAND_PAGE, jar=jar)
    items, last_exc, ok, total = [], None, False, 1
    page = 1
    while page <= min(total, BRAND_MAX_PAGES):
        try:
            d = json.loads(get(f'{BRAND_API}{page}', headers={'Referer': BRAND_PAGE, 'X-Requested-With': 'XMLHttpRequest'},
                               jar=jar).decode('utf-8'))
            items += brand_items(d.get('data') or [])
            total = int((d.get('paginationInfo') or {}).get('totalPageCount') or 1)
            ok = True
        except Exception as e:
            last_exc = e
        page += 1
    if not ok and last_exc:
        raise last_exc
    return items
