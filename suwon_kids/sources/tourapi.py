"""한국관광공사 TourAPI 행사정보(searchFestival2). 관광공사에 등록된 큰 축제만 있어서 보조 출처.
수원 행사는 시 포털이 더 자세하므로 근교 시 주소만 받는다. 키는 .env TOURAPI_KEY (Decoding 키)."""
import json
import re
import urllib.parse
from datetime import date, datetime

from suwon_kids import ai, http, week
from suwon_kids.models import Event

API = 'https://apis.data.go.kr/B551011/KorService2'
NEAR = re.compile(r'(용인|화성|안양|의왕|오산|군포)시')
GYEONGGI = '41'


def _get(op: str, **params) -> dict:
    key = ai.env().get('TOURAPI_KEY')
    if not key:
        raise RuntimeError('TOURAPI_KEY 없음')
    q = urllib.parse.urlencode({'serviceKey': key, 'MobileOS': 'ETC', 'MobileApp': 'suwonkids', '_type': 'json', **params})
    d = json.loads(http.get(f'{API}/{op}?{q}'))['response']
    if d['header']['resultCode'] != '0000':
        raise RuntimeError(f"TourAPI {d['header']['resultCode']} {d['header']['resultMsg']}")
    return d['body']


def items(body: dict) -> list[dict]:
    it = (body.get('items') or {}).get('item') or []
    return [it] if isinstance(it, dict) else it


def homepage(raw: str | None) -> str | None:
    """'<a href="...">', 'www.x.com', '공식 홈페이지 https://x' 모두 있다. URL이 없으면 None."""
    m = re.search(r'href="(https?://[^"]+)"', raw or '') or re.search(r'https?://[^\s"<>]+', raw or '')
    if m:
        return m.group(m.lastindex or 0)
    m = re.search(r'www\.[^\s"<>]+', raw or '')
    return 'https://' + m.group(0) if m else None


def _ymd(s: str) -> date:
    return datetime.strptime(s, '%Y%m%d').date()


def to_event(item: dict, url: str | None) -> Event:
    return Event(
        id=f"tour:{item['contentid']}",
        source='tour',
        title=item['title'].strip(),
        start=_ymd(item['eventstartdate']),
        end=_ymd(item['eventenddate']),
        time=None,
        place=item.get('addr2') or item['addr1'],
        address=item['addr1'],
        url=url or 'https://search.naver.com/search.naver?query=' + urllib.parse.quote(item['title']),
        target='누구나',
    )


def fetch(today: date | None = None, get=_get) -> list[Event]:
    rng = week.this_week(today or date.today())
    found, page = [], 1
    while page <= 5:
        body = get('searchFestival2', eventStartDate=f'{rng[0]:%Y%m%d}', lDongRegnCd=GYEONGGI, numOfRows=100, pageNo=page)
        found += items(body)
        if page * 100 >= int(body.get('totalCount') or 0):
            break
        page += 1
    out = []
    for it in found:
        if not NEAR.search(it.get('addr1', '')) or _ymd(it['eventstartdate']) > rng[1]:
            continue
        try:
            url = homepage(items(get('detailCommon2', contentId=it['contentid']))[0].get('homepage'))
        except Exception:
            url = None
        out.append(to_event(it, url))
    return out
