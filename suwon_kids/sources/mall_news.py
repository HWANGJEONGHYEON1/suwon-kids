"""백화점·쇼핑몰 팝업 뉴스. 매장 이름으로 네이버 뉴스를 검색하고, Gemini가 기사 요약문에서 행사만 뽑는다.
naver.py와 같은 흐름. 날짜가 기사에 안 보이면 버리고, 원문 링크는 기사로 건다."""
import re
from datetime import date, timedelta

from suwon_kids import ai
from suwon_kids.mall_info import MALLS
from suwon_kids.models import MallItem
from suwon_kids.sources import naver

# 검색어 → 매장 이름. 같은 매장을 다른 이름으로 쓰는 기사도 있다
QUERY_NAMES = {'타임빌라스 의왕': '타임빌라스 의왕', '롯데아울렛 의왕': '타임빌라스 의왕', '타임빌라스 수원': '타임빌라스 수원',
               '롯데백화점 평촌점': '롯데백화점 평촌', '롯데몰 광교': '롯데몰 광교', '스타필드 수원': '스타필드 수원',
               '현대백화점 판교': '현대백화점 판교', 'AK플라자 수원': 'AK플라자 수원'}
KEYWORDS = ('팝업', '키즈', '체험')
AHEAD_DAYS = 14  # 오늘부터 이만큼 뒤까지 시작하는 행사만

PROMPT = """오늘은 {today}입니다. 아래는 백화점·쇼핑몰 관련 뉴스 기사 요약입니다.
기사에서 아래 매장 안에서 열리는 아이·가족 대상 팝업스토어, 체험, 공연, 키즈 브랜드 행사만 찾아 JSON 배열로만 답하세요.
매장: {malls}

규칙:
- 기사에 날짜가 적힌 행사만. 날짜가 없으면 뺍니다. "31일"처럼 월이 없으면 기사 발행일 기준으로 연·월을 채웁니다.
- {today} 이전에 끝난 행사, 위 매장이 아닌 곳의 행사, 어른만 가는 행사, 일반 할인·세일은 뺍니다.
- mall은 위 매장 이름 중 하나 그대로.
- 기사에 없는 내용은 지어내지 말고, 모르면 null.

형식: [{{"n": 기사번호, "mall": "매장", "title": "행사명", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "place": "층·장소" 또는 null}}]
행사가 없으면 []

기사:
{articles}"""


def to_item(row: dict, art: dict) -> MallItem | None:
    mall, title = row.get('mall'), (row.get('title') or '').strip()
    start, end = naver._day(row.get('start')), naver._day(row.get('end') or row.get('start'))
    source_text = f"{art['title']} {art['text']}"
    if not (mall in MALLS and title and start and end and start <= end and naver.mentions(source_text, start)):
        return None
    return MallItem(
        id=f"mallnews:{mall}:{start}:{re.sub(r'\W', '', title)}",
        source='mallnews',
        mall=mall,
        title=title,
        brand=None,
        start=start,
        end=end,
        place=(row.get('place') or '').strip(),
        url=art['link'],
    )


def fetch(today: date | None = None, search=naver._search, gen=ai.generate) -> list[MallItem]:
    today = today or date.today()
    last = today + timedelta(days=AHEAD_DAYS)
    results, errors = [], []
    for q in (f'{n} {k}' for n in QUERY_NAMES for k in KEYWORDS):
        try:
            results.append(search(q))
        except Exception as e:  # 검색어 하나가 실패해도 나머지로 간다
            errors.append(e)
    if not results and errors:
        raise errors[-1]
    arts = naver.articles(results, today)
    out, seen, failed = [], set(), 0
    for i in range(0, len(arts), naver.BATCH):
        batch = arts[i:i + naver.BATCH]
        listing = '\n'.join(f"[{n}] 발행일 {a['pub']} | {a['title']} | {a['text']}" for n, a in enumerate(batch))
        try:
            rows = naver._parse(gen(PROMPT.format(today=today, malls=', '.join(MALLS), articles=listing)))
        except Exception as e:  # 묶음 하나가 실패해도 앞뒤 묶음 결과는 지킨다
            errors.append(e)
            failed += 1
            continue
        for row in rows:
            n = row.get('n')
            if not isinstance(n, int) or not 0 <= n < len(batch):
                continue
            it = to_item(row, batch[n])
            if it and it.id not in seen and it.end >= today and it.start <= last:
                seen.add(it.id)
                out.append(it)
    if arts and failed == -(-len(arts) // naver.BATCH):
        raise errors[-1]
    return out
