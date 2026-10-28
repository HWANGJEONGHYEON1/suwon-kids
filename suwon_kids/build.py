"""전체 실행: 수집 → 이번 주 → 상세(주최·본문) → 거르기 → 동네 → 중복 → 요약 → site/events.json, index.html.
모든 출처가 실패하거나 결과가 0건이면 기존 파일을 건드리지 않는다.
사용: python3 -m suwon_kids.build"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from suwon_kids import ai, areas, dedupe, filters, render, summarize, week
from suwon_kids.models import Event
from suwon_kids.sources import gyeonggi, kopis, naver, starfield, suwon_portal, tourapi

ROOT = Path(__file__).parent.parent


def default_sources() -> dict[str, Callable[[], list[Event]]]:
    return {
        'suwon': lambda: suwon_portal.to_events(suwon_portal.fetch_list()),
        'starfield': lambda: [e for r in starfield.fetch() for e in starfield.to_events(r)],
        'ggac': gyeonggi.fetch_ggac,
        'kopis': kopis.fetch,
        'tour': tourapi.fetch,
        'naver': naver.fetch,
    }


def _month_day(s: str) -> tuple[int, int] | None:
    m = re.match(r'\s*(\d{1,2})\s*[.월/]\s*(\d{1,2})', s or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


def _poster_line(ev: Event, poster: dict) -> str | None:
    key = (ev.start.month, ev.start.day)
    progs = [p for p in poster.get('programs', []) if p.get('name') and _month_day(p.get('date')) == key]
    parts = []
    for p in progs:
        extra = f" ({p['age']})" if p.get('age') else ''
        parts.append(' '.join(x for x in (p['name'], p.get('time')) if x) + extra)
    line = ', '.join(parts)
    return line[:summarize.MAX_LEN] or None


def ev_unknown_festival(ev: Event) -> bool:
    return ev.host == '확인 못 함'


def _write(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def run(today: date, out_dir: Path, sources: dict, detail=suwon_portal.fetch_detail, gen=ai.generate,
        poster_cache: Path = ROOT / 'state/posters.json', now: datetime | None = None) -> dict:
    rng = week.this_week(today)
    counts, errors, found = {}, {}, []
    for name, fetch in sources.items():
        try:
            evs = [e for e in fetch() if week.overlaps(e, rng)]
            counts[name] = len(evs)
            found += evs
        except Exception as e:  # 한 출처가 죽어도 나머지는 계속
            errors[name] = f'{type(e).__name__}: {e}'
    bodies = {}
    for ev in found:
        if ev.source == 'suwon':
            try:
                d = detail(ev.id.split(':', 1)[1])
                ev.host, bodies[ev.id] = d['host'] or None, d['body']
            except Exception as e:
                errors.setdefault('detail', f'{type(e).__name__}: {e}')
                if filters.FESTIVAL.search(ev.title):
                    ev.host = '확인 못 함'  # 상세를 못 읽은 축제는 빠뜨리지 않는다 (실패 기준 2)
    kept = [e for e in found if filters.keep(e) or ev_unknown_festival(e)]
    for ev in kept:
        ev.area = areas.assign(ev)
    kept = dedupe.merge(kept)
    if not kept:
        return {'ok': False, 'counts': counts, 'errors': errors or {'all': '0건'}}

    cache = json.loads(poster_cache.read_text(encoding='utf-8')) if poster_cache.exists() else {}
    long_events, events = [e for e in kept if week.is_long(e)], [e for e in kept if not week.is_long(e)]
    for ev in events:
        if ev.source == 'starfield' and ev.image:
            poster = summarize.read_poster(ev.image, cache, gen=gen)
            ev.summary = _poster_line(ev, poster) if poster else None
        elif ev.id in bodies:
            ev.summary = summarize.one_line(ev, bodies[ev.id], gen=gen)
    poster_cache.parent.mkdir(parents=True, exist_ok=True)
    _write(poster_cache, json.dumps(cache, ensure_ascii=False, indent=1))

    now = now or datetime.now()

    def js(e: Event) -> dict:
        return {**e.to_json(), 'festival': filters.is_host_exception(e.title, e.host)}

    out_dir.mkdir(parents=True, exist_ok=True)
    data = {'updated': now.isoformat(timespec='minutes'), 'week': [rng[0].isoformat(), rng[1].isoformat()],
            'events': [js(e) for e in sorted(events, key=lambda e: (e.start, e.title))],
            'long': [js(e) for e in sorted(long_events, key=lambda e: e.title)]}
    _write(out_dir / 'events.json', json.dumps(data, ensure_ascii=False, indent=1))
    festivals = {e.id for e in kept if filters.is_host_exception(e.title, e.host)}
    _write(out_dir / 'index.html', render.page(events, long_events, now, rng, festivals))
    return {'ok': True, 'counts': counts, 'errors': errors}


if __name__ == '__main__':
    r = run(date.today(), ROOT / 'site', default_sources())
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0 if r['ok'] else 1)
