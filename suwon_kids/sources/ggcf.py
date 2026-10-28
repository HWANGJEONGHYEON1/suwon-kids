"""경기문화재단 뮤지엄 (둘 다 용인 기흥구 상갈동): 경기도어린이박물관 행사·교육, 경기도박물관 문화행사.
목록은 최근 등록순 5~10건씩이고 지난 행사도 섞여 있어, 앞쪽 몇 쪽만 읽고 이번 주와 겹치는 것만 남긴다.
백남준아트센터는 같은 재단이지만 장기 프로그램·성인 대상이 대부분이라 뺐다."""
import html
import re
from datetime import date

from suwon_kids import http, week
from suwon_kids.models import Event

ADDRESS = '경기도 용인시 기흥구 상갈로 6'
GCM, MUSE = 'https://gcm.ggcf.kr', 'https://musenet.ggcf.kr'
PAGES = 4
ADULT = re.compile(r'성인|청소년 이상|어른')
GROUP = re.compile(r'단체')  # 어린이집·학교 단체 예약은 가족이 갈 수 없다
ONSITE = re.compile(r'박물관|전시실|교육실|로비|\d층|야외|마당')  # 이 밖의 장소는 주소를 몰라 뺀다
OFFSITE = re.compile(r'도서관|아트센터|문화원|문화재단|대학|학교|전역')  # '경기도서관 지하 1층'처럼 층이 있어도 다른 기관
RANGE = re.compile(r'(\d{4}-\d{2}-\d{2})\([^)]*\)\s*~\s*(\d{4}-\d{2}-\d{2})')


def _text(s: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def parse_gcm(page: str) -> list[dict]:
    """어린이박물관 카드: 링크, 상태(진행중/종료), 제목, 표(대상·행사기간|교육기간·장소·참가비)."""
    out = []
    for li in re.split(r'<li>\s*<div class="exhibition-img-area"', page)[1:]:
        link = re.search(r'class="link-plus" href="([^"]+)"', li)
        title = re.search(r'<h4>(.*?)</h4>', li, re.S)
        if not (link and title):
            continue
        rows = {_text(k): _text(v) for k, v in re.findall(r'<th>(.*?)</th>\s*<td[^>]*>(.*?)</td>', li, re.S)}
        status = re.search(r'chk-mark[^"]*">\s*<p>([^<]+)', li)
        out.append({'url': link.group(1), 'title': _text(title.group(1)), 'status': status.group(1).strip() if status else '',
                    'period': rows.get('행사기간') or rows.get('교육기간') or '', 'place': rows.get('장소', ''),
                    'target': rows.get('대상', ''), 'price': rows.get('참가비')})
    return out


def parse_muse(page: str) -> list[dict]:
    """경기도박물관 카드: <a class="inner"> 안에 제목과 기간·장소·대상 dl."""
    out = []
    for link, body in re.findall(r'<div class="list_box04">\s*<a href="([^"]+)" class="inner">(.*?)</a>', page, re.S):
        title = re.search(r'<p class="title">(.*?)</p>', body, re.S)
        rows = {_text(k): _text(v) for k, v in re.findall(r'<dt>(.*?)</dt>\s*<dd>(.*?)</dd>', body, re.S)}
        if title:
            out.append({'url': link, 'title': _text(title.group(1)), 'status': '', 'period': rows.get('기간', ''),
                        'place': rows.get('장소', ''), 'target': rows.get('대상', ''), 'price': None})
    return out


def to_event(row: dict, museum: str) -> Event | None:
    m = RANGE.search(row['period'])
    if (not m or row['status'] == '종료' or ADULT.search(row['target']) or GROUP.search(row['title'] + row['target'])
            or (row['place'] and (OFFSITE.search(row['place']) or not ONSITE.search(row['place'])))):  # '경기도 전역'·다른 기관에서 여는 행사
        return None
    return Event(
        id=f"ggcf:{row['url'].split('//', 1)[-1]}",
        source='ggcf',
        title=row['title'],
        start=date.fromisoformat(m.group(1)),
        end=date.fromisoformat(m.group(2)),
        time=None,
        place=row['place'] or museum,
        address=ADDRESS,
        url=row['url'],
        target='어린이' if museum == '경기도어린이박물관' else '누구나',  # 어린이박물관은 전부 아이 대상
        host=museum,
        age=row['target'] or None,
        price=row['price'] or None,
    )


def fetch(today: date | None = None, get=http.get) -> list[Event]:
    rng = week.this_week(today or date.today())
    lists = [(f'{GCM}/events', parse_gcm, '경기도어린이박물관'), (f'{GCM}/edus', parse_gcm, '경기도어린이박물관'),
             (f'{MUSE}/events', parse_muse, '경기도박물관')]
    out, seen = [], set()
    for url, parse, museum in lists:
        for n in range(1, PAGES + 1):
            rows = parse(get(f'{url}?page={n}').decode('utf-8', 'replace'))
            for row in rows:
                ev = to_event(row, museum)
                if ev and ev.id not in seen and week.overlaps(ev, rng):
                    seen.add(ev.id)
                    out.append(ev)
            if not rows:
                break
    return out
