"""백화점·쇼핑몰 행사 모으기. 출처별로 받아 → 기간 → 아이 대상(규칙 → Gemini, 결과는 캐시) → 중복 합치기 → malls.json.
events.json 에는 넣지 않는다."""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from suwon_kids import ai
from suwon_kids.mall_info import MALLS
from suwon_kids.models import Event, MallItem
from suwon_kids.sources import ak, hyundai, lotte, mall_news, naver, starfield

ROOT = Path(__file__).resolve().parents[1]
LEAD_DAYS = 14  # 오늘부터 이만큼 뒤까지 시작하는 행사만
BATCH = 20
DROP = re.compile('카드|무이자|할부|사은|캐시백|멤버십|멤버스|마일리지|주차|세차|약국|입점|키오스크|상품권|웨딩|혼수|시네마|골프|화장품|뷰티|생활가전|가전제품|가구|푸드|떡집|청과|과일|핫도그|타코야끼|유정란|반지|주얼리|아이더|K2그룹')
KEEP = re.compile('키즈|아동|유아|베이비|주니어|어린이|캐릭터|토이|장난감|레고|체험|곤충|파충류|공룡|텔레토비|뽀로로|티니핑|산리오|디즈니')
SHOP = re.compile('할인|%|프로모션|promotion|신상품|균일가|아우터|early bird|brand week|시즌오프')
PLAY = re.compile('팝업|pop-up|체험|공연|전시|캐릭터|곤충|파충류')
COMMON = {'팝업', 'pop', 'up', 'store', '스토어', '오픈', 'open', '이벤트', '행사', '키즈', 'kids', '체험', '진행'}

PROMPT = """아래는 백화점·쇼핑몰 행사 목록입니다. 한 줄은 `[번호] 매장 | 브랜드 | 제목 | 장소` 입니다.
각 행사가 8세 이하 아이를 데리고 갈 만한 행사인지 엄격하게 판단하세요.
kid true: 캐릭터·키즈 팝업, 아이 대상 체험·공연·전시, 아이 옷·신발·용품 판매·할인이 제목·브랜드에 드러나는 것.
kid false: 어른·일반 패션·스포츠·아웃도어 브랜드 할인(나이키·유니클로·아이더 등 키즈 표시가 없는 것), 카드·사은·멤버십 혜택, 식당·식품·카페, 영화관, 잡화·주얼리, 가구·가전.
kind는 보고 노는 것(팝업·체험·공연·전시)이면 play, 아이 옷·용품 판매·할인이면 shop.
[{{"n": 번호, "kid": true 또는 false, "kind": "play" 또는 "shop"}}] JSON 배열로만 답하세요.

{items}"""


def _text(it: MallItem) -> str:
    return f'{it.brand or ""} {it.title} {it.place}'


def rule(it: MallItem) -> bool | None:
    """True 남김 / False 뺌 / None 모름 (뺌이 먼저)."""
    text = _text(it)
    if DROP.search(text):
        return False
    return True if KEEP.search(text) else None


def kind_of(it: MallItem) -> str | None:
    text = _text(it).lower()
    if SHOP.search(text):
        return 'shop'
    return 'play' if PLAY.search(text) else None


def _ask(batch: list[MallItem], gen) -> dict[int, dict]:
    lines = '\n'.join(f'[{n}] {i.mall} | {i.brand or ""} | {i.title} | {i.place}' for n, i in enumerate(batch))
    out = {}
    for row in naver._parse(gen(PROMPT.format(items=lines))):
        n = row.get('n')
        if isinstance(n, int) and 0 <= n < len(batch):
            kid = row.get('kid') is True
            kind = row.get('kind') if row.get('kind') in ('play', 'shop') else None
            out[n] = {'kid': kid, 'kind': kind if kid else None}
    return out


def classify(items: list[MallItem], cache: dict, gen=ai.generate) -> list[MallItem]:
    """아이 대상만 남기고 kind 를 채운다. 규칙으로 모르면 Gemini(20개씩), 결과는 cache 에 넣는다. 실패한 묶음은 캐시 없이 그날 뺀다."""
    unknown = [i for i in items if rule(i) is None and i.id not in cache]
    for at in range(0, len(unknown), BATCH):
        batch = unknown[at:at + BATCH]
        try:
            answers = _ask(batch, gen)
        except Exception as e:
            print(f'백화점 행사 분류 실패 ({len(batch)}개): {type(e).__name__}: {e}', file=sys.stderr)
            continue
        for n, ans in answers.items():
            cache[batch[n].id] = ans
    out = []
    for it in items:
        r = rule(it)
        if r is None:
            got = cache.get(it.id)
            if not got or not got.get('kid'):
                continue
            it.kind = got.get('kind') or kind_of(it) or 'shop'
        elif r:
            it.kind = kind_of(it) or 'shop'
        else:
            continue
        out.append(it)
    return out


def _words(it: MallItem) -> set[str]:
    parts = re.split(r'\W+', f'{it.brand or ""} {it.title}'.lower())
    return {p for p in parts if len(p) >= 2 and p not in COMMON}


def merge(items: list[MallItem]) -> list[MallItem]:
    """공식 출처를 먼저 두고, 뉴스 항목은 같은 매장·기간 겹침·낱말 공유인 공식 항목이 있으면 버린다."""
    seen, official = set(), []
    for it in items:
        if it.source != 'mallnews' and it.id not in seen:
            seen.add(it.id)
            official.append(it)
    out = list(official)
    for it in items:
        if it.source != 'mallnews' or it.id in seen:
            continue
        words = _words(it)
        if not any(o.mall == it.mall and o.start <= it.end and it.start <= o.end and words & _words(o) for o in official):
            seen.add(it.id)
            out.append(it)
    return out


def default_sources() -> dict:
    return {'lotte': lotte.fetch, 'hyundai': hyundai.fetch, 'ak': ak.fetch, 'starfield': starfield.fetch_brand, 'news': mall_news.fetch}


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)


def collect(today: date, sources: dict | None = None, gen=ai.generate,
            cache_path: Path = ROOT / 'state/mall_kids.json') -> tuple[list[MallItem], dict[str, int], dict[str, str]]:
    """(항목, 출처별 건수, 출처별 오류). 출처 하나가 실패해도 나머지는 계속."""
    sources = default_sources() if sources is None else sources
    found, counts, errors = [], {}, {}
    for name, fetch in sources.items():
        try:
            got = fetch(today)
        except Exception as e:
            errors[name] = f'{type(e).__name__}: {e}'
            continue
        counts[name] = len(got)
        found += got
    last = today + timedelta(days=LEAD_DAYS)
    near = [i for i in found if i.end >= today and i.start <= last]
    cache = _load(cache_path)
    before = json.dumps(cache, sort_keys=True)
    kept = classify(near, cache, gen)
    if json.dumps(cache, sort_keys=True) != before:
        _save(cache_path, cache)
    return sorted(merge(kept), key=lambda i: (i.start, i.mall, i.title)), counts, errors


def to_event(it: MallItem) -> Event:
    place = f'{it.mall} · {it.place}' if it.place else it.mall
    title = f'[{it.brand}] {it.title}' if it.brand else it.title
    return Event(it.id, it.source, title, it.start, it.end, None, place, MALLS[it.mall], it.url, '누구나', area='백화점')


def write(items: list[MallItem], today: date, path: Path) -> int:
    _save(path, {'updated': today.isoformat(), 'malls': [i.to_json() for i in items]})
    return len(items)
