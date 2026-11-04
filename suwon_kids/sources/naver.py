"""근교 축제·걷기대회·가족 행사. 시 보도자료가 기사로만 나와서 네이버 뉴스 검색으로 기사를 모으고,
Gemini가 기사 요약문에서 행사 일정만 뽑는다. 수원은 시 포털이 있으니 뺀다.
키는 .env NAVER_CLIENT_ID / NAVER_CLIENT_SECRET. 날짜가 기사에 안 보이면 버리고, 원문 링크는 기사로 건다."""
import email.utils
import html
import json
import re
import urllib.parse
from datetime import date, datetime, timedelta

from suwon_kids import ai, http, summarize, week
from suwon_kids.models import Event

API = 'https://openapi.naver.com/v1/search/news.json'
# 탭 이름 → 주소. 주소의 '동탄'·'OO시'로 areas.assign이 탭을 고른다
PLACES = {'동탄': '경기도 화성시 동탄구', '용인': '경기도 용인시', '화성': '경기도 화성시', '안양': '경기도 안양시',
          '의왕': '경기도 의왕시', '오산': '경기도 오산시', '군포': '경기도 군포시'}
KEYWORDS = ('축제', '걷기대회', '가족 행사')
RECENT_DAYS = 21  # 이보다 오래된 기사는 보지 않는다
BATCH = 20

PROMPT = """오늘은 {today}입니다. 아래는 경기도 {places} 지역 뉴스 기사 요약입니다.
기사에서 아이와 가족이 갈 수 있는 행사(축제, 걷기대회, 체험, 공연, 장터 등)를 찾아 JSON 배열로만 답하세요.

규칙:
- 기사에 날짜가 적힌 행사만. "31일"처럼 월이 없으면 기사 발행일 기준으로 연·월을 채웁니다.
- {today} 이전에 끝난 행사, 모집·공모·교육·회의·기념식, 어른만 가는 행사는 뺍니다.
- city는 행사가 열리는 곳: {places} 중 하나. 동탄에서 열리면 "동탄". 그 밖의 지역이면 뺍니다.
- 기사에 없는 내용은 쓰지 말고, 모르면 null.

형식: [{{"n": 기사번호, "title": "행사명", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "time": "HH:MM" 또는 null,
"place": "장소", "city": "용인", "summary": "무엇을 하는지 한 줄(30자 이내)" 또는 null}}]
행사가 없으면 []

기사:
{articles}"""


def _search(query: str) -> dict:
    cfg = ai.env()
    cid, secret = cfg.get('NAVER_CLIENT_ID'), cfg.get('NAVER_CLIENT_SECRET')
    if not cid or not secret:
        raise RuntimeError('NAVER_CLIENT_ID/NAVER_CLIENT_SECRET 없음')
    q = urllib.parse.urlencode({'query': query, 'display': 50, 'sort': 'date'})
    return json.loads(http.get(f'{API}?{q}', {'X-Naver-Client-Id': cid, 'X-Naver-Client-Secret': secret}))


def _clean(s: str) -> str:
    return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()


def articles(results: list[dict], today: date) -> list[dict]:
    """여러 검색 결과를 합쳐 최근 기사만, 링크 기준 중복 없이."""
    seen, out = set(), []
    for res in results:
        for it in res.get('items', []):
            link = it.get('originallink') or it['link']
            pub = email.utils.parsedate_to_datetime(it['pubDate']).date()
            if link in seen or pub < today - timedelta(days=RECENT_DAYS):
                continue
            seen.add(link)
            out.append({'title': _clean(it['title']), 'text': _clean(it['description']), 'link': link, 'pub': pub})
    return out


def _parse(raw: str) -> list[dict]:
    m = re.search(r'\[.*\]', raw, re.S)
    try:
        rows = json.loads(m.group(0)) if m else []
    except ValueError:
        return []
    return [r for r in rows if isinstance(r, dict)]


def _day(s) -> date | None:
    try:
        return datetime.strptime(str(s), '%Y-%m-%d').date()
    except ValueError:
        return None


def mentions(text: str, d: date) -> bool:
    """기사에 그 날짜가 보이는가: '31일', '10월 31', '10.31', '10/31'. '9월 28일'의 '28일'은 다른 달이라 안 친다."""
    return bool(re.search(rf'(?<![\d월./])(?<!월 ){d.day}일|(?<!\d){d.month}\s*월\s*{d.day}(?!\d)'
                          rf'|(?<!\d){d.month}\s*[./]\s*{d.day}(?!\d)', text))


# 백화점 7곳의 장소 이름: 칸마다 하나 이상 들어 있어야 한다 (제목의 '롯데 후원' 같은 말에는 속지 않게 장소만 본다)
MALL_PLACES = ((('타임빌라스',),), (('아울렛',), ('의왕',)), (('스타필드 수원', '스타필드수원'),), (('롯데백화점',), ('평촌',)),
               (('롯데몰',), ('광교',)), (('현대백화점',), ('판교',)), (('AK플라자', 'AK 플라자'), ('수원',)))


def is_mall_event(place: str) -> bool:
    """장소가 백화점 7곳 중 하나인가."""
    text = place.upper()
    return any(all(any(w.upper() in text for w in group) for group in groups) for groups in MALL_PLACES)


def to_event(row: dict, art: dict) -> Event | None:
    start, end = _day(row.get('start')), _day(row.get('end') or row.get('start'))
    city, title, place = row.get('city'), (row.get('title') or '').strip(), (row.get('place') or '').strip()
    source_text = f"{art['title']} {art['text']}"
    if not (start and end and start <= end and city in PLACES and title and place and mentions(source_text, start)):
        return None
    if is_mall_event(place):
        return None  # 백화점 7곳 행사는 백화점 탭에 있다
    summary = row.get('summary')
    return Event(
        id=f"naver:{city}:{start}:{re.sub(r'\W', '', title)}",
        source='naver',
        title=title,
        start=start,
        end=end,
        time=row.get('time') or None,
        place=place,
        address=f'{PLACES[city]} {place}',  # 지도 검색이 도시 전체가 아니라 행사장을 찾게
        url=art['link'],
        target='누구나',
        summary=summary if summary and summarize.verified(summary, source_text) else None,
    )


def fetch(today: date | None = None, search=_search, gen=ai.generate) -> list[Event]:
    today = today or date.today()
    rng = week.this_week(today)
    results, errors = [], []
    for q in (f'{p} {k}' for p in PLACES for k in KEYWORDS):
        try:
            results.append(search(q))
        except Exception as e:  # 검색어 하나가 실패해도 나머지로 간다
            errors.append(e)
    if not results and errors:
        raise errors[-1]
    arts = articles(results, today)
    out, seen, failed = [], set(), 0
    for i in range(0, len(arts), BATCH):
        batch = arts[i:i + BATCH]
        listing = '\n'.join(f"[{n}] 발행일 {a['pub']} | {a['title']} | {a['text']}" for n, a in enumerate(batch))
        try:
            rows = _parse(gen(PROMPT.format(today=today, places=', '.join(PLACES), articles=listing)))
        except Exception as e:  # 묶음 하나가 실패해도 앞뒤 묶음 결과는 지킨다
            errors.append(e)
            failed += 1
            continue
        for row in rows:
            n = row.get('n')
            if not isinstance(n, int) or not 0 <= n < len(batch):
                continue
            ev = to_event(row, batch[n])
            if ev and ev.id not in seen and week.overlaps(ev, rng) and not any(same(ev, o) for o in out):
                seen.add(ev.id)
                out.append(ev)
    if arts and failed == -(-len(arts) // BATCH):
        raise errors[-1]
    return out


# 제목에 흔해서 같은 행사의 증거가 못 되는 낱말 (도시 이름은 따로 뺀다)
COMMON = re.compile(r'축제|행사|팝업|팝업스토어|스토어|오픈|이벤트|체험|가족|걷기대회|페스타|페스티벌|마켓|장터|공연|전시|프로그램'
                    r'|겨울|가을|여름|봄|함께하는|특별|\d{4}')


VENUE = re.compile(r'(공원|광장|호수|센터|시청|극장|아트홀|박물관|도서관|운동장|체육관)$')


def _tokens(title: str, places: list[str]) -> set[str]:
    """제목의 핵심 낱말. 도시·흔한 말·장소 이름(두 행사 중 하나의 장소에 들어 있거나 …공원 같은 꼴)은 같은 행사의 증거가 못 된다."""
    cities = {c for p in PLACES for c in (p, p + '시')}
    places = [p.lower() for p in places if len(p) >= 2]
    return {t for t in re.split(r'\W+', title.lower())
            if len(t) >= 2 and t not in cities and not COMMON.fullmatch(t) and not VENUE.search(t)
            and not any(t in p or p in t for p in places)}


def _share(a: set[str], b: set[str]) -> bool:
    """같은 낱말, 또는 짧은 쪽(3자 이상)이 긴 쪽의 앞부분 ('텔레토비' / '텔레토비와')."""
    return any(x == y or (min(len(x), len(y)) >= 3 and (x.startswith(y) or y.startswith(x))) for x in a for y in b)


def same(a: Event, b: Event) -> bool:
    """기사마다 행사 이름을 다르게 쓴다: '행복 걷기대회'와 '안양시민과 함께하는 행복걷기대회'는 같은 행사.
    같은 시에서 기간이 겹치고, 한쪽 제목이 다른 쪽에 들어 있거나 핵심 낱말을 나누면 같은 행사로 본다."""
    if a.address.split()[1] != b.address.split()[1] or not (a.start <= b.end and b.start <= a.end):
        return False
    ka, kb = (re.sub(r'\W', '', e.title) for e in (a, b))
    places = [a.place, b.place]
    return ka in kb or kb in ka or _share(_tokens(a.title, places), _tokens(b.title, places))
