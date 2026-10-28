"""공연예술통합전산망(KOPIS) 아동 공연 (kidstate=Y). 수원·근교 시군구별 목록 → 상세(시간·공연장 id) → 공연장(주소).
키는 .env KOPIS_KEY. KOPIS 데이터를 쓰면 출처 표기가 의무다 (render 푸터)."""
import re
import time
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date, datetime

from suwon_kids import ai, http, week
from suwon_kids.models import Event

API = 'http://kopis.or.kr/openApi/restful'
VIEW = 'https://kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id='
CITIES = {'수원': '4111', '용인': '4146', '화성': '4159', '안양': '4117', '의왕': '4143', '오산': '4137', '군포': '4141'}
TAG = re.compile(r'\s*\[[^\]]*\]')  # 제목·공연장 끝의 "[화성]", "[수원 장안]"
MAX_TIME = 40


GAP = 1.0             # 호출 사이 최소 간격(초). 몰아서 5번쯤 부르면 한동안 전부 400이 난다
BACKOFF = (5, 15)     # 400이 나면 이만큼 쉬고 다시
_last = [0.0]


def _get(path: str, sleep=time.sleep, clock=time.monotonic, **params) -> bytes:
    key = ai.env().get('KOPIS_KEY')
    if not key:
        raise RuntimeError('KOPIS_KEY 없음')
    url = f'{API}/{path}?' + urllib.parse.urlencode({'service': key, **params})
    for wait in (*BACKOFF, None):
        sleep(max(0.0, _last[0] + GAP - clock()))
        _last[0] = clock()
        try:
            return http.get(url)
        except urllib.error.HTTPError as e:
            if e.code != 400 or wait is None:
                raise
            sleep(wait)


def rows(xml: bytes | str) -> list[dict]:
    out = []
    for d in ET.fromstring(xml).findall('db'):
        r = {c.tag: (c.text or '').strip() for c in d}
        r['booking'] = next((u.text.strip() for u in d.iter('relateurl') if (u.text or '').strip()), '')
        out.append(r)
    return out


def short_time(t: str) -> str:
    """'토요일(14:00,19:00), 일요일(11:00)' → '토 14:00·19:00 / 일 11:00'."""
    t = re.sub(r'([월화수목금토일])요일', r'\1', t)
    t = re.sub(r'\s*\(([^)]*)\)', lambda m: ' ' + m.group(1).replace(',', '·'), t)
    t = t.replace(', ', ' / ')
    return t if len(t) <= MAX_TIME else t[:MAX_TIME] + '…'


def _day(s: str) -> date:
    return datetime.strptime(s, '%Y.%m.%d').date()


def to_event(row: dict, detail: dict, address: str) -> Event:
    t = detail.get('dtguidance')
    poster = row.get('poster') or None
    return Event(
        id=f"kopis:{row['mt20id']}",
        source='kopis',
        title=TAG.sub('', row['prfnm']).strip(),
        start=_day(row['prfpdfrom']),
        end=_day(row['prfpdto']),
        time=short_time(t) if t else None,
        place=TAG.sub('', row['fcltynm']).strip(),
        address=address,
        url=VIEW + row['mt20id'],
        target='어린이',
        image=re.sub(r'^https?://(www\.)?kopis\.or\.kr', 'https://kopis.or.kr', poster) if poster else None,
        age=detail.get('prfage') or None,
        price=detail.get('pcseguidance') or None,
        booking=detail.get('booking') or None,
    )


def fetch(today: date | None = None, get=_get) -> list[Event]:
    rng = week.this_week(today or date.today())
    seen, out, places, failed = set(), [], {}, []
    for city, code in CITIES.items():
        # KOPIS가 새벽에 가끔 400을 준다. 한 번 더 해 보고, 그래도 안 되면 그 도시만 건너뛴다
        for attempt in range(2):
            try:
                listing = rows(get('pblprfr', stdate=f'{rng[0]:%Y%m%d}', eddate=f'{rng[1]:%Y%m%d}', cpage=1, rows=100,
                                   signgucode='41', signgucodesub=code, kidstate='Y'))
                break
            except Exception as e:
                listing, err = None, e
        if listing is None:
            failed.append(err)
            continue
        for row in listing:
            if row['mt20id'] in seen:
                continue
            seen.add(row['mt20id'])
            detail, address = {}, f'경기도 {city}시'  # 상세·공연장을 못 읽어도 도시 탭에는 넣는다
            try:
                detail = rows(get(f"pblprfr/{row['mt20id']}"))[0]
                fid = detail.get('mt10id')
                if fid and fid not in places:
                    places[fid] = rows(get(f'prfplc/{fid}'))[0].get('adres') or None
                address = places.get(fid) or address
            except Exception:
                pass
            out.append(to_event(row, detail, address))
    if len(failed) == len(CITIES):
        raise failed[-1]
    return out
