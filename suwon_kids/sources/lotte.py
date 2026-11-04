"""롯데 4개 지점 행사. 지점은 파라미터가 아니라 쿠키로 정해져서, 지점 페이지에서 쿠키를 받고 목록(HTML 조각)을 POST로 받는다."""
import html
import re
from datetime import date, timedelta
from urllib.parse import urlencode

from suwon_kids import http
from suwon_kids.models import MallItem

SITE = 'https://www.lotteshopping.com'
LIST_URL = f'{SITE}/contents/shpgInfoList'
# 지점코드 -> (매장 이름, 목록에 찍히는 지점 표기)
STORES = {
    '0406': ('타임빌라스 의왕', '프리미엄 아울렛 의왕점'),
    '0349': ('타임빌라스 수원', '타임빌라스 수원'),
    '0341': ('롯데백화점 평촌', '백화점 평촌점'),
    '0355': ('롯데몰 광교', '쇼핑몰 광교점'),
}
TYPES = ('C00903', 'C00908')  # 쇼핑뉴스, 문화/이벤트
MAX_PAGES = 8
SIZE = 12

_PERIOD = re.compile(r'(?:(\d{2})\.)?(\d{1,2})\.(\d{1,2})\s*\([^)]*\)\s*~\s*(?:(\d{2})\.)?(\d{1,2})\.(\d{1,2})')
_GO_URL = re.compile(r"goUrl\('([^']+)',\s*'([^']+)'\)")


def parse_period(txt: str, today: date) -> tuple[date, date] | None:
    """'10.28(수) ~ 11.8(일)' 같은 기간. 해가 없으면 오늘 기준으로 채운다. '11.3(화) OPEN'처럼 끝이 없으면 None."""
    m = _PERIOD.search(txt or '')
    if not m:
        return None
    sy, sm, sd, ey, em, ed = m.groups()
    try:
        if ey:
            end = date(2000 + int(ey), int(em), int(ed))
        else:
            end = date(today.year, int(em), int(ed))
            if end < today - timedelta(days=60):
                end = end.replace(year=end.year + 1)
        if sy:
            return date(2000 + int(sy), int(sm), int(sd)), end
        start = date(end.year, int(sm), int(sd))
        if start > end:
            start = start.replace(year=start.year - 1)
        return start, end
    except ValueError:
        return None


def _text(s: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def _title(raw: str) -> tuple[str | None, str]:
    """제목 칸을 <br>로 나눠 앞이 [브랜드]면 brand로 뗀다."""
    parts = [_text(p) for p in re.split(r'<br\s*/?>', raw, flags=re.I)]
    brand = None
    m = re.match(r'\[([^\]]+)\]\s*(.*)$', parts[0])
    if m:
        brand, parts[0] = m.group(1).strip(), m.group(2)
    return brand, ' '.join(p for p in parts if p)


def parse_list(html_text: str, code: str, today: date) -> list[MallItem]:
    mall, branch = STORES[code]
    out = []
    for li in re.findall(r'<li class="content-item.*?</li>', html_text, re.S):
        go, title, info, dt = (re.search(p, li, re.S) for p in (
            _GO_URL.pattern, r'class="__title[^"]*"[^>]*>(.*?)</div>',
            r'class="__info">(.*?)</div>', r'class="__date">(.*?)</div>'))
        if not (go and title and info and dt):
            continue
        spans = [_text(s) for s in re.findall(r'<span>(.*?)</span>', info.group(1), re.S)]
        if not spans or spans[0] != branch:  # 다른 지점·전점·온라인 행사는 버린다
            continue
        period = parse_period(_text(dt.group(1)), today)
        brand, name = _title(title.group(1))
        if not period or not (name or brand):
            continue
        kind, nid = go.group(1), go.group(2)
        out.append(MallItem(
            id=f'lotte:{code}:{nid}',
            source='lotte',
            mall=mall,
            title=name or brand,
            brand=brand,
            start=period[0],
            end=period[1],
            place=spans[-1] if len(spans) > 1 else '',
            url=(f'{SITE}/shpgnews/shpgnewsDetail?shpgNewsNo={nid}' if kind == 'C00903'
                 else f'{SITE}/contents/shpgInfo?cstrCd={code}'),
        ))
    return out


def _last_val(html_text: str, name: str) -> str | None:
    """같은 조각에 스크립트가 둘 있으면 뒤의 값을 쓴다."""
    vals = re.findall(rf"\[name='{name}'\]\"\)\.val\(\"([^\"]*)\"\)", html_text)
    return vals[-1] if vals else None


def paging(html_text: str) -> tuple[int, bool]:
    total = _last_val(html_text, 'totalCnt')
    return (int(total) if total and total.isdigit() else 0), _last_val(html_text, 'hasNextYn') == 'Y'


def fetch(today: date, get=http.get) -> list[MallItem]:
    items, last_exc, ok = [], None, False
    for code in STORES:
        jar = http.new_jar()
        try:
            get(f'{SITE}/store/main?cstrCd={code}', jar=jar)
        except Exception as e:
            last_exc = e
            continue
        for tp in TYPES:
            total = 0
            try:
                for page in range(1, MAX_PAGES + 1):
                    body = urlencode({'cntsTpCd': tp, 'page': page, 'size': SIZE, 'totalCnt': total}).encode()
                    h = get(LIST_URL, headers={'X-Requested-With': 'XMLHttpRequest',
                                               'Content-Type': 'application/x-www-form-urlencoded',
                                               'Referer': f'{SITE}/store/main?cstrCd={code}'},
                            jar=jar, data=body).decode('utf-8')
                    items += parse_list(h, code, today)
                    cnt, has_next = paging(h)
                    if page == 1:
                        total = cnt
                    if not has_next:
                        break
                ok = True
            except Exception as e:
                last_exc = e
    if not ok and last_exc:
        raise last_exc
    return items
