"""여러 출처에 같은 행사가 있으면 하나로. 시 포털 쪽을 남긴다."""
import re

from suwon_kids.models import Event


def _key(title: str) -> str:
    return re.sub(r'\s|20\d\d|[()\[\]<>《》「」년]', '', title)


def merge(events: list[Event]) -> list[Event]:
    out: list[Event] = []
    for ev in sorted(events, key=lambda e: e.source != 'suwon'):
        if not any(_key(o.title) == _key(ev.title) and o.start <= ev.end and ev.start <= o.end for o in out):
            out.append(ev)
    return out
