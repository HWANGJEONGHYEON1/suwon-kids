"""아이와 갈 만한 행사만 남긴다. 수원시·경기도 주최 축제는 대상·제목 규칙과 상관없이 남긴다 (기간 규칙은 별도)."""
import re

from suwon_kids.models import Event

EXCLUDE_WORDS = ('모집', '수강생', '경로', '채용', '참가자', '학술', '아카데미', '행사달력', '포럼', '세미나', '설명회')
KID_TARGETS = ('어린이', '누구나')
FESTIVAL = re.compile(r'축제|페스티벌|페스타|문화제|야행|마켓|장터')


def is_host_exception(title: str, host: str | None) -> bool:
    return bool(host) and ('수원' in host or '경기' in host) and bool(FESTIVAL.search(title))


def keep(ev: Event) -> bool:
    if is_host_exception(ev.title, ev.host):
        return True
    if any(w in ev.title for w in EXCLUDE_WORDS):
        return False
    return any(t in ev.target for t in KID_TARGETS)
