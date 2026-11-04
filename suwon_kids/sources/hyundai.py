"""현대백화점 판교 행사. 지점 페이지에서 이달의 DM 코드를 읽고, 종류별 목록(JSON)을 받는다."""
import json
import re
from datetime import date
from urllib.parse import urlencode

from suwon_kids import http
from suwon_kids.models import MallItem

MALL = '현대백화점 판교'
PAGE = 'https://www.ehyundai.com/newPortal/SN/SN_0101000.do?branchCd=B00148000'
API = 'https://www.ehyundai.com/newPortal/SN/GetCmsContentsAJX.do'
TYPES = ('01', '03')  # 쇼핑뉴스, 문화이벤트

_DM_CODE = re.compile(r"curtMblDmCd\s*=\s*'([^']+)'")


def dm_code(html: str) -> str:
    """월마다 바뀌는 DM 코드. 없으면 페이지가 바뀐 것이라 예외."""
    m = _DM_CODE.search(html)
    if not m:
        raise ValueError('curtMblDmCd not found')
    return m.group(1)


def _day(s) -> date | None:
    """'20261108000000' 앞 8자리. 비었거나 공백(전각 포함)이면 None."""
    s = (s or '').strip()
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8])) if len(s) >= 8 and s[:8].isdigit() else None
    except ValueError:
        return None


def _place(it: dict) -> str:
    floor = ((it.get('evntFlrCd') or {}).get('label') or '').strip()
    spot = (it.get('evntPlceNm') or '').strip()
    return ' '.join(p for p in ('' if floor == '미입력' else floor, spot) if p)


def parse(data: dict) -> list[MallItem]:
    out = []
    for it in ((data.get('result') or {}).get('items')) or []:
        title = re.sub(r'\s+', ' ', it.get('evntCrdNm') or '').strip()
        start, end = _day(it.get('expsEvntStartDt')), _day(it.get('expsEvntEndDt'))
        if not (it.get('evntCrdCd') and title and start and end):  # 기간이 불확실하면 버린다
            continue
        out.append(MallItem(
            id=f"hyundai:{it['evntCrdCd']}",
            source='hyundai',
            mall=MALL,
            title=title,
            brand=None,
            start=start,
            end=end,
            place=_place(it),
            url=it.get('onelink') or PAGE,
        ))
    return out


def fetch(today: date, get=http.get) -> list[MallItem]:
    jar = http.new_jar()
    code = dm_code(get(PAGE, jar=jar).decode('utf-8'))
    items, seen, last_exc, ok = [], set(), None, False
    for tp in TYPES:
        param = f'mblDmCd={code}&evntCrdTypeCd={tp}&pageSize=50&page=1'
        try:
            body = get(f'{API}?{urlencode({"apiID": "ifAppHdcms012", "param": param})}',
                       headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': PAGE}, jar=jar)
            parsed = parse(json.loads(body.decode('utf-8')))
            ok = True
        except Exception as e:
            last_exc = e
            continue
        items += [i for i in parsed if i.id not in seen]
        seen.update(i.id for i in parsed)
    if not ok and last_exc:
        raise last_exc
    return items
