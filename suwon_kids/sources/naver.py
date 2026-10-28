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


def to_event(row: dict, art: dict) -> Event | None:
    start, end = _day(row.get('start')), _day(row.get('end') or row.get('start'))
    city, title, place = row.get('city'), (row.get('title') or '').strip(), (row.get('place') or '').strip()
    source_text = f"{art['title']} {art['text']}"
    if not (start and end and start <= end and city in PLACES and title and place and mentions(source_text, start)):
        return None
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


def same(a: Event, b: Event) -> bool:
    """기사마다 행사 이름을 다르게 쓴다: '행복 걷기대회'와 '안양시민과 함께하는 행복걷기대회'는 같은 행사."""
    ka, kb = (re.sub(r'\W', '', e.title) for e in (a, b))
    return a.address.split()[1] == b.address.split()[1] and a.start == b.start and (ka in kb or kb in ka)
