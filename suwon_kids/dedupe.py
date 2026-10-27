"""여러 출처에 같은 행사가 있으면 하나로. 시 포털 쪽을 남긴다.
동네가 다르면 합치지 않는다 (KOPIS는 제목에서 지역을 떼므로 도시가 다른 같은 제목 공연이 있다)."""
import re

from suwon_kids.models import Event


def _key(title: str) -> str:
    return re.sub(r'\s|20\d\d|[()\[\]<>《》「」년]', '', title)


def merge(events: list[Event]) -> list[Event]:
    out: list[Event] = []
    for ev in sorted(events, key=lambda e: e.source != 'suwon'):
        if not any(o.area == ev.area and _key(o.title) == _key(ev.title)
                   and o.start <= ev.end and ev.start <= o.end for o in out):
            out.append(ev)
    return out
