"""index.html. 지역 탭(전체·수원·동탄·근교 시) → 지역 안에서 동네별 카드 → 지역별 상시 묶음(접힘).
카드는 <details>라 누르면 상세(포스터·연령·가격·주소·지도·예매·원문)가 펼쳐진다. JS가 없으면 탭은 해당 지역으로 이동하는 링크다."""
import re
import urllib.parse
from datetime import date, datetime
from html import escape

from suwon_kids.areas import ORDER, REGIONS, region
from suwon_kids.models import Event

TITLE = '이번 주 수원·근교, 애랑 갈 만한 곳'
SOURCES = ('수원특례시 행사축제포털, 스타필드 수원, 경기아트센터, 한국관광공사 TourAPI'
           ' · 공연 출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)')
WEEKDAY = '월화수목금토일'
PROGRAM = re.compile(r'^\[[^\]]{6,}\]\s*(?=\S{2})')  # 제목 앞 "[경기도 공연장 상주단체 육성지원사업 …]" 같은 사업명
MAP = 'https://map.naver.com/p/search/'

# 레이아웃: 좁은 한 단, 위에 고정 지역 탭, 아래로 동네 소제목과 펼침 카드
CSS = """
:root{--bg:#faf8f4;--card:#fff;--fg:#211f1b;--muted:#6f6a61;--line:#e7e1d6;--accent:#f0b400;--accent-ink:#7a5800;
--accent-soft:#fdf3d3;--on-accent:#211f1b;--chip:#efeae0;--ui:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard","Noto Sans KR",sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#17161a;--card:#222126;--fg:#eeece8;--muted:#a6a3ad;--line:#35333b;
--accent:#e0a800;--accent-ink:#f2c94c;--accent-soft:#3a3120;--chip:#2c2a31;color-scheme:dark}}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 var(--ui);-webkit-text-size-adjust:100%}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);background:var(--bg);z-index:10}
.wrap{max-width:600px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
header.top{padding-block:22px 6px}
h1{font-size:21px;line-height:1.3;margin:0;text-wrap:balance;letter-spacing:-.01em}
.week{color:var(--muted);font-size:13px;margin:4px 0 0;font-variant-numeric:tabular-nums}
nav.tabs{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);border-bottom:1px solid var(--line)}
nav.tabs .wrap{display:flex;gap:6px;overflow-x:auto;padding-block:10px;scrollbar-width:none}
nav.tabs .wrap::-webkit-scrollbar{display:none}
a.tab{flex:none;display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:999px;background:var(--chip);
color:var(--fg);text-decoration:none;font-size:14px;font-weight:600;white-space:nowrap}
a.tab .n{font-weight:500;color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
a.tab[aria-selected="true"]{background:var(--fg);color:var(--bg)}
a.tab[aria-selected="true"] .n{color:inherit;opacity:.7}
a.tab:focus-visible,summary:focus-visible,.acts a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
main{padding-block:4px 40px}
section.region{display:flex;flex-direction:column;gap:8px;padding-top:18px;scroll-margin-top:60px}
h2{font-size:18px;margin:0;display:flex;align-items:baseline;gap:8px}
h2 .n{font-size:13px;color:var(--muted);font-weight:500}
h3{font-size:13px;font-weight:700;color:var(--accent-ink);margin:10px 0 0;letter-spacing:.02em}
details.card{background:var(--card);border:1px solid var(--line);border-radius:12px}
details.card>summary{list-style:none;cursor:pointer;padding:11px 34px 11px 12px;display:grid;gap:3px;position:relative}
details.card>summary::after{content:"";position:absolute;right:14px;top:16px;width:7px;height:7px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(45deg)}
details.card[open]>summary::after{transform:rotate(-135deg);top:20px}
details.card>summary::-webkit-details-marker{display:none}
details.card[open]>summary{border-bottom:1px dashed var(--line)}
.t{font-weight:650;line-height:1.4}
.m{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.s{font-size:14px}
.badges{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}
.b{font-size:11.5px;font-weight:600;padding:1px 7px;border-radius:6px;background:var(--chip);color:var(--muted)}
.b.kind{background:var(--accent-soft);color:var(--accent-ink)}
.more{padding:10px 12px 12px;display:grid;gap:10px}
.info{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:start}
.info img{width:92px;max-width:100%;border-radius:8px;border:1px solid var(--line)}
dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:14px}
dt{color:var(--muted)}dd{margin:0;min-width:0;overflow-wrap:anywhere}
dd a{color:var(--accent-ink)}
.acts{display:flex;flex-wrap:wrap;gap:6px}
.acts a{padding:7px 12px;border-radius:8px;border:1px solid var(--line);color:var(--fg);text-decoration:none;font-size:14px;font-weight:600}
.acts a.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
details.long{margin-top:6px}
details.long>summary{cursor:pointer;color:var(--muted);font-size:14px;font-weight:600;padding:6px 0}
details.long>div{display:flex;flex-direction:column;gap:8px}
.empty{color:var(--muted);margin:0}
footer{color:var(--muted);font-size:12px;padding-block:8px 32px;line-height:1.6}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
"""

JS = """
(function(){var tabs=[].slice.call(document.querySelectorAll('a.tab')),secs=[].slice.call(document.querySelectorAll('section.region')),nav=document.querySelector('nav.tabs');
function show(r){tabs.forEach(function(t){t.setAttribute('aria-selected',t.dataset.r===r)});
secs.forEach(function(s){s.hidden=r!=='all'&&s.id!==r});try{localStorage.setItem('region',r)}catch(e){}}
tabs.forEach(function(t){t.addEventListener('click',function(e){e.preventDefault();show(t.dataset.r);
try{history.replaceState(null,'','#'+t.dataset.r)}catch(e){}if(window.scrollY>nav.offsetTop)window.scrollTo(0,nav.offsetTop);
t.scrollIntoView({block:'nearest',inline:'nearest'})})});
function valid(r){return tabs.some(function(t){return t.dataset.r===r})}
window.addEventListener('hashchange',function(){var h=location.hash.slice(1);if(valid(h))show(h)});
var r=location.hash.slice(1);if(!r){try{r=localStorage.getItem('region')}catch(e){}}
show(valid(r)?r:'all')})();
"""


def fmt_day(d: date) -> str:
    return f'{d.month}.{d.day}({WEEKDAY[d.weekday()]})'


def fmt_range(ev: Event) -> str:
    return fmt_day(ev.start) if ev.start == ev.end else f'{fmt_day(ev.start)}~{fmt_day(ev.end)}'


def display_title(title: str) -> str:
    return PROGRAM.sub('', title)


def _kind(ev: Event, festival: bool) -> str | None:
    if ev.source == 'kopis':
        return '공연'
    if ev.source == 'tour' or festival:
        return '축제'
    return None


def _card(ev: Event, festival: bool = False) -> str:
    meta = ' · '.join(x for x in (fmt_range(ev), ev.time, ev.place) if x)
    kind = _kind(ev, festival)
    badges = ''.join([f'<span class="b kind">{kind}</span>' if kind else '',
                      f'<span class="b">{escape(ev.age)}</span>' if ev.age else ''])
    head = (f'<summary><span class="t">{escape(display_title(ev.title))}</span><span class="m">{escape(meta)}</span>'
            + (f'<span class="badges">{badges}</span>' if badges else '')
            + (f'<span class="s">{escape(ev.summary)}</span>' if ev.summary else '') + '</summary>')
    where = ev.address or ev.place
    rows = [('일시', ' · '.join(x for x in (fmt_range(ev), ev.time) if x))]
    if ev.place:
        rows.append(('장소', ev.place))
    if where:
        rows.append(('주소', f'<a href="{MAP}{urllib.parse.quote(where)}" target="_blank" rel="noopener">{escape(where)}</a>'))
    rows += [(k, v) for k, v in (('연령', ev.age), ('가격', ev.price), ('대상', None if ev.source == 'kopis' else ev.target)) if v]
    dl = ''.join(f'<dt>{k}</dt><dd>{v if k == "주소" else escape(v)}</dd>' for k, v in rows)
    img = f'<img src="{escape(ev.image)}" alt="" loading="lazy">' if ev.image and ev.source == 'kopis' else ''
    acts = ((f'<a class="primary" href="{escape(ev.booking)}" target="_blank" rel="noopener">예매하기</a>' if ev.booking else '')
            + f'<a href="{escape(ev.url)}" target="_blank" rel="noopener">원문 보기</a>')
    return f'<details class="card">{head}<div class="more"><div class="info"><dl>{dl}</dl>{img}</div><div class="acts">{acts}</div></div></details>'


def _region_html(name: str, events: list[Event], long_events: list[Event], festivals: set[str]) -> str:
    out = []
    areas = [a for a in ORDER if any((e.area or '기타') == a for e in events)]
    for area in areas:
        group = sorted((e for e in events if (e.area or '기타') == area), key=lambda e: (e.start, e.title))
        label = '그 밖의 수원' if area == '기타' else area
        if len(areas) > 1 or area != name:
            out.append(f'<h3>{escape(label)}</h3>')
        out += [_card(e, e.id in festivals) for e in group]
    if not events:
        out.append('<p class="empty">이번 주 일정은 없고 상시 행사만 있어요.</p>')
    if long_events:
        cards = ''.join(_card(e, e.id in festivals) for e in sorted(long_events, key=lambda e: e.title))
        out.append(f'<details class="long"><summary>상시 전시·행사 {len(long_events)}곳</summary><div>{cards}</div></details>')
    n = len(events) + len(long_events)
    return (f'<section class="region" id="{REGIONS[name]}"><h2>{escape(name)} <span class="n">{n}</span></h2>'
            + ''.join(out) + '</section>')


def page(events: list[Event], long_events: list[Event], updated: datetime, week: tuple[date, date] | None = None,
         festivals: set[str] | None = None) -> str:
    festivals = festivals or set()
    week_line = f'<p class="week">{fmt_day(week[0])} ~ {fmt_day(week[1])}</p>' if week else ''
    names = [r for r in REGIONS if any(region(e.area) == r for e in events + long_events)]
    sections = ''.join(_region_html(r, [e for e in events if region(e.area) == r],
                                    [e for e in long_events if region(e.area) == r], festivals) for r in names)
    total = len(events) + len(long_events)
    tabs = (f'<a class="tab" href="#" data-r="all" aria-selected="true">전체 <span class="n">{total}</span></a>'
            + ''.join(f'<a class="tab" href="#{REGIONS[r]}" data-r="{REGIONS[r]}">{escape(r)} '
                      f'<span class="n">{sum(region(e.area) == r for e in events + long_events)}</span></a>' for r in names))
    nav = f'<nav class="tabs" aria-label="지역"><div class="wrap">{tabs}</div></nav>' if names else ''
    body = sections or '<p class="empty">이번 주 행사가 아직 없어요.</p>'
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{TITLE}</title>'
            f'<link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="apple-touch-icon.png">'
            f'<meta name="apple-mobile-web-app-title" content="수원 아이랑"><meta name="theme-color" content="#f0b400">'
            f'<style>{CSS}</style></head><body>'
            f'<header class="top"><div class="wrap"><h1>{TITLE}</h1>{week_line}</div></header>{nav}'
            f'<main class="wrap">{body}</main>'
            f'<footer class="wrap">마지막 갱신 {updated:%Y-%m-%d %H:%M} · 출처: {SOURCES}</footer>'
            f'<script>{JS}</script></body></html>')
