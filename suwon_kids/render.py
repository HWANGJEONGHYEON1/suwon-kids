"""index.html. 동네별 섹션(행사 없는 동네는 숨김) + 상시 묶음. 태그 없음."""
from datetime import date, datetime
from html import escape

from suwon_kids.areas import AREAS
from suwon_kids.models import Event

TITLE = '이번 주 수원, 애랑 갈 만한 곳'
ORDER = [a['name'] for a in AREAS] + ['장안구', '권선구', '팔달구', '영통구', '기타']
WEEKDAY = '월화수목금토일'

CSS = """
:root{--bg:#faf8f4;--card:#fff;--fg:#222;--muted:#777;--line:#e6e2da;--accent:#f0b400}
@media (prefers-color-scheme:dark){:root{--bg:#17161a;--card:#222126;--fg:#eee;--muted:#a6a3ad;--line:#35333b;--accent:#e0a800}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif}
main{max-width:560px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:20px;margin:4px 0 2px}.week{color:var(--muted);font-size:13px;margin:0 0 8px}
h2{font-size:16px;margin:22px 0 8px;padding-bottom:3px;border-bottom:2px solid var(--accent)}
a.card{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin-bottom:8px;color:inherit;text-decoration:none}
.t{font-weight:600}.m{color:var(--muted);font-size:13px}.s{font-size:14px;margin-top:2px}
.empty{color:var(--muted)}footer{color:var(--muted);font-size:12px;margin-top:28px}
"""


def fmt_day(d: date) -> str:
    return f'{d.month}.{d.day}({WEEKDAY[d.weekday()]})'


def fmt_range(ev: Event) -> str:
    return fmt_day(ev.start) if ev.start == ev.end else f'{fmt_day(ev.start)}~{fmt_day(ev.end)}'


def _card(ev: Event) -> str:
    meta = ' · '.join(x for x in (fmt_range(ev), ev.time, ev.place) if x)
    summary = f'<div class="s">{escape(ev.summary)}</div>' if ev.summary else ''
    return (f'<a class="card" href="{escape(ev.url)}" target="_blank" rel="noopener">'
            f'<div class="t">{escape(ev.title)}</div><div class="m">{escape(meta)}</div>{summary}</a>')


def _sections(events: list[Event]) -> str:
    out = []
    for area in ORDER:
        group = sorted((e for e in events if (e.area or '기타') == area), key=lambda e: (e.start, e.title))
        if group:
            out.append(f'<h2>{escape(area)}</h2>' + ''.join(_card(e) for e in group))
    return ''.join(out)


def page(events: list[Event], long_events: list[Event], updated: datetime, week: tuple[date, date] | None = None) -> str:
    week_line = f'<p class="week">{fmt_day(week[0])} ~ {fmt_day(week[1])}</p>' if week else ''
    body = _sections(events) or '<p class="empty">이번 주 행사가 아직 없어요.</p>'
    long_html = f'<h2>상시 전시·행사</h2>' + ''.join(_card(e) for e in sorted(long_events, key=lambda e: e.title)) if long_events else ''
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{TITLE}</title>'
            f'<style>{CSS}</style></head><body><main><h1>{TITLE}</h1>{week_line}{body}{long_html}'
            f'<footer>마지막 갱신 {updated:%Y-%m-%d %H:%M} · 출처: 수원특례시 행사축제포털, 스타필드 수원</footer>'
            f'</main></body></html>')
