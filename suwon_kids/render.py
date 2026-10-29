"""index.html. 지역 탭(전체·수원·동탄·근교 시) → 지역 안에서 날짜(오늘·내일·요일)별 흰 리스트 → 지역별 상시 묶음(접힘).
행은 토스 TDS ListRow 꼴(제목 17px / 시간 / 동네·장소)이고 <details>라 누르면 상세(한 줄 소개·포스터·연령·가격·주소·지도·예매·원문)가
펼쳐진다. 여러 날 행사는 이번 주 안의 첫날에 한 번만 나온다. JS가 없으면 탭은 해당 지역으로 이동하는 링크다."""
import re
import urllib.parse
from datetime import date, datetime
from html import escape

from suwon_kids import filters
from suwon_kids.areas import ORDER, REGIONS, region
from suwon_kids.models import Event

TITLE = '이번 주 수원·근교, 애랑 갈 만한 곳'
SOURCES = ('수원특례시 행사축제포털, 스타필드 수원, 경기아트센터, 경기도어린이박물관·경기도박물관, 안양시 문화예술행사일정,'
           ' 화성시 문화관광, 군포시 주간행사계획, 한국관광공사 TourAPI, 네이버 뉴스 검색'
           ' · 공연 출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)')
WEEKDAY = '월화수목금토일'
PROGRAM = re.compile(r'^\[[^\]]{6,}\]\s*(?=\S{2})')  # 제목 앞 "[경기도 공연장 상주단체 육성지원사업 …]" 같은 사업명
MAP = 'https://map.naver.com/p/search/'
CITY_SOURCES = ('naver', 'anyang', 'hwaseong', 'gunpo')  # 주최 정보 없이 제목으로 축제를 가리는 근교 출처
GOATCOUNTER = 'https://suwon-kids.goatcounter.com/count'  # 방문자 통계(쿠키 없음). 비우면 스크립트를 넣지 않는다

# 레이아웃: 토스 TDS 꼴. 회색 바탕 위 흰 리스트, 행은 ListRow(위아래 16px·좌우 20px, 들여 쓴 구분선),
# 글자는 TDS 스케일(t3 22 / t4 20 / t5 17 / t6 15 / t7 13)과 회색 단계(grey900·700·500·400). 강조색만 노랑
CSS = """
:root{--bg:#f2f4f6;--surface:#fff;--fg:#191f28;--sub:#4e5968;--muted:#8b95a1;--faint:#b0b8c1;--line:#e5e8eb;--fill:#f2f4f6;
--accent:#f0b400;--accent-ink:#8a5f00;--accent-soft:#fff3cc;--on-accent:#191f28;
--ui:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard","Noto Sans KR",sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#101013;--surface:#1d1d22;--fg:#f2f4f6;--sub:#c3c9d0;--muted:#8b95a1;--faint:#5c636c;
--line:#2c2c34;--fill:#2c2c34;--accent:#e0a800;--accent-ink:#f2c94c;--accent-soft:#3a3120;--on-accent:#191f28;color-scheme:dark}}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 var(--ui);-webkit-text-size-adjust:100%;word-break:keep-all}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);background:var(--surface);z-index:10}
.wrap{max-width:600px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
header.top{background:var(--surface);padding-block:24px 4px}
h1{font-size:22px;line-height:31px;font-weight:700;margin:0;text-wrap:balance;letter-spacing:-.02em}
.week{color:var(--muted);font-size:15px;margin:2px 0 0;font-variant-numeric:tabular-nums}
nav.tabs{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--surface);border-bottom:1px solid var(--line)}
nav.tabs .wrap{display:flex;gap:8px;overflow-x:auto;padding-block:12px;scrollbar-width:none}
nav.tabs .wrap::-webkit-scrollbar{display:none}
a.tab{flex:none;display:inline-flex;align-items:center;gap:4px;padding:8px 14px;border-radius:999px;background:var(--fill);
color:var(--sub);text-decoration:none;font-size:15px;font-weight:600;white-space:nowrap}
a.tab .n{font-weight:500;color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
a.tab[aria-selected="true"]{background:var(--fg);color:var(--surface)}
a.tab[aria-selected="true"] .n{color:inherit;opacity:.65}
a.tab:focus-visible,summary:focus-visible,.acts a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
main{padding-block:8px 48px}
section.region{display:flex;flex-direction:column;padding-top:24px;scroll-margin-top:64px}
h2{font-size:20px;line-height:29px;font-weight:700;margin:0 4px 4px;display:flex;align-items:baseline;gap:6px;letter-spacing:-.01em}
h2 .n{font-size:15px;color:var(--muted);font-weight:600}
h3.day{font-size:15px;line-height:22px;font-weight:700;color:var(--sub);margin:0;padding:16px 4px 8px}
h3.day .d{color:var(--muted);font-weight:500;margin-left:4px;font-variant-numeric:tabular-nums}
.list{background:var(--surface);border-radius:16px;overflow:hidden}
.list>details+details{position:relative}
.list>details+details::before{content:"";position:absolute;top:0;left:20px;right:0;border-top:1px solid var(--line)}
details.row>summary{list-style:none;cursor:pointer;padding:16px 48px 16px 20px;display:grid;gap:2px;position:relative;-webkit-tap-highlight-color:transparent}
details.row>summary:active{background:var(--fill)}
details.row>summary::-webkit-details-marker{display:none}
details.row>summary::after{content:"";position:absolute;right:22px;top:24px;width:8px;height:8px;border-right:2px solid var(--faint);border-bottom:2px solid var(--faint);transform:rotate(45deg)}
details.row[open]>summary::after{transform:rotate(-135deg);top:28px}
details.row>summary>*{min-width:0;overflow-wrap:anywhere}
.t{font-size:17px;line-height:25.5px;font-weight:600;letter-spacing:-.01em}
.m{display:flex;flex-wrap:wrap;align-items:center;gap:6px;color:var(--sub);font-size:15px;line-height:22.5px;font-variant-numeric:tabular-nums}
.p{color:var(--muted);font-size:15px;line-height:22.5px}
.b{font-size:12px;line-height:18px;font-weight:600;padding:1px 6px;border-radius:5px;background:var(--fill);color:var(--sub)}
.b.kind{background:var(--accent-soft);color:var(--accent-ink)}
.more{padding:0 20px 20px;display:grid;gap:14px}
.s{margin:0;font-size:15px;line-height:22.5px;color:var(--sub)}
.info{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:start}
.info img{width:88px;max-width:100%;border-radius:10px}
dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:15px;line-height:22.5px}
dt{color:var(--muted)}dd{margin:0;min-width:0;overflow-wrap:anywhere}
dd a{color:var(--fg);text-decoration-color:var(--faint);text-underline-offset:3px}
.acts{display:flex;flex-wrap:wrap;gap:8px}
.acts a{padding:10px 16px;border-radius:10px;background:var(--fill);color:var(--fg);text-decoration:none;font-size:15px;font-weight:600}
.acts a.primary{background:var(--accent);color:var(--on-accent)}
details.long{margin-top:8px}
details.long>summary{list-style:none;cursor:pointer;color:var(--sub);font-size:15px;font-weight:600;padding:14px 4px 8px}
details.long>summary::-webkit-details-marker{display:none}
details.long>summary::before{content:"+ ";color:var(--muted)}
details.long[open]>summary::before{content:"− "}
.empty{color:var(--muted);margin:0;padding:12px 4px 0;font-size:15px}
footer{color:var(--muted);font-size:13px;padding-block:8px 32px;line-height:19.5px}
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
    if ev.source == 'ggcf':
        return '체험'
    if ev.source == 'tour' or festival or (ev.source in CITY_SOURCES and filters.FESTIVAL.search(ev.title)):
        return '축제'
    return None


def _when(ev: Event, day: date | None) -> str:
    """리스트 둘째 줄. 날짜 제목 아래에서는 그날 하루 행사면 시간만, 여러 날이면 끝나는 날을 붙인다."""
    if day is None or ev.start != ev.end:
        span = f'~{fmt_day(ev.end)}까지' if day is not None else fmt_range(ev)
        return ' · '.join(x for x in (span, ev.time) if x)
    return re.sub(rf'^{WEEKDAY[day.weekday()]}\s+', '', ev.time or '')  # 토요일 제목 아래 '토 11:00' → '11:00'


def _card(ev: Event, festival: bool = False, day: date | None = None, show_area: bool = False) -> str:
    kind = _kind(ev, festival)
    when = _when(ev, day)
    meta = (f'<span class="b kind">{kind}</span>' if kind else '') + (f'<span>{escape(when)}</span>' if when else '')
    area = ev.area if show_area and ev.area and ev.area != '기타' and ev.area not in (ev.place or '') else None
    where = ' · '.join(x for x in (area, ev.place) if x)
    head = (f'<summary><span class="t">{escape(display_title(ev.title))}</span>'
            + (f'<span class="m">{meta}</span>' if meta else '')
            + (f'<span class="p">{escape(where)}</span>' if where else '') + '</summary>')
    where = ev.address or ev.place
    rows = [('일시', ' · '.join(x for x in (fmt_range(ev), ev.time) if x))]
    if ev.place:
        rows.append(('장소', ev.place))
    if where:
        rows.append(('주소', f'<a href="{MAP}{urllib.parse.quote(where)}" target="_blank" rel="noopener">{escape(where)}</a>'))
    rows += [(k, v) for k, v in (('연령', ev.age), ('가격', ev.price), ('대상', None if ev.source == 'kopis' else ev.target)) if v]
    dl = ''.join(f'<dt>{k}</dt><dd>{v if k == "주소" else escape(v)}</dd>' for k, v in rows)
    img = f'<img src="{escape(ev.image)}" alt="" loading="lazy">' if ev.image and ev.source == 'kopis' else ''
    link = '기사 보기' if ev.source == 'naver' else '원문 보기'
    acts = ((f'<a class="primary" href="{escape(ev.booking)}" target="_blank" rel="noopener" data-goatcounter-click="booking" '
             f'data-goatcounter-title="{escape(display_title(ev.title))}">예매하기</a>' if ev.booking else '')
            + f'<a href="{escape(ev.url)}" target="_blank" rel="noopener">{link}</a>')
    summary = f'<p class="s">{escape(ev.summary)}</p>' if ev.summary else ''
    return (f'<details class="row">{head}<div class="more">{summary}<div class="info"><dl>{dl}</dl>{img}</div>'
            f'<div class="acts">{acts}</div></div></details>')


def day_label(d: date, today: date) -> str:
    rel = {0: '오늘', 1: '내일'}.get((d - today).days, f'{WEEKDAY[d.weekday()]}요일')
    return f'{rel}<span class="d">{d.month}.{d.day}</span>'


def _start_time(ev: Event) -> str:
    """'토 11:00·14:00' → '11:00'. 출처마다 요일이 붙거나 안 붙어서 표시 문자열로는 정렬이 틀린다."""
    m = re.search(r'(\d{1,2}):(\d{2})', ev.time or '')
    return f'{int(m.group(1)):02d}:{m.group(2)}' if m else '99:99'


def _area_rank(ev: Event) -> int:
    return ORDER.index(ev.area) if ev.area in ORDER else len(ORDER)


def _region_html(name: str, events: list[Event], long_events: list[Event], festivals: set[str], today: date) -> str:
    out = []
    show_area = any(e.area != name for e in events + long_events)  # 수원처럼 동네가 여럿이면 장소 앞에 동네를 붙인다
    by_day: dict[date, list[Event]] = {}
    for e in events:  # 여러 날 행사는 이번 주 안의 첫날에만
        by_day.setdefault(max(e.start, today), []).append(e)
    for day in sorted(by_day):
        group = sorted(by_day[day], key=lambda e: (_start_time(e), _area_rank(e), e.title))
        out.append(f'<h3 class="day">{day_label(day, today)}</h3>'
                   f'<div class="list">{"".join(_card(e, e.id in festivals, day, show_area) for e in group)}</div>')
    if not events:
        out.append('<p class="empty">이번 주 일정은 없어요.</p>')
    if long_events:
        rows = ''.join(_card(e, e.id in festivals, None, show_area)  # 날짜 제목이 없으니 시작일까지 전체 기간
                       for e in sorted(long_events, key=lambda e: (_area_rank(e), e.title)))
        out.append(f'<details class="long"><summary>상시 전시·행사 {len(long_events)}곳</summary>'
                   f'<div class="list">{rows}</div></details>')
    n = len(events) + len(long_events)
    return (f'<section class="region" id="{REGIONS[name]}"><h2>{escape(name)} <span class="n">{n}</span></h2>'
            + ''.join(out) + '</section>')


def page(events: list[Event], long_events: list[Event], updated: datetime, week: tuple[date, date] | None = None,
         festivals: set[str] | None = None) -> str:
    festivals = festivals or set()
    week_line = f'<p class="week">{fmt_day(week[0])} ~ {fmt_day(week[1])}</p>' if week else ''
    today = week[0] if week else updated.date()
    names = [r for r in REGIONS if any(region(e.area) == r for e in events + long_events)]
    sections = ''.join(_region_html(r, [e for e in events if region(e.area) == r],
                                    [e for e in long_events if region(e.area) == r], festivals, today) for r in names)
    total = len(events) + len(long_events)
    tabs = (f'<a class="tab" href="#" data-r="all" aria-selected="true">전체 <span class="n">{total}</span></a>'
            + ''.join(f'<a class="tab" href="#{REGIONS[r]}" data-r="{REGIONS[r]}">{escape(r)} '
                      f'<span class="n">{sum(region(e.area) == r for e in events + long_events)}</span></a>' for r in names))
    nav = f'<nav class="tabs" aria-label="지역"><div class="wrap">{tabs}</div></nav>' if names else ''
    body = sections or '<p class="empty">이번 주 행사가 아직 없어요.</p>'
    stats = f'<script data-goatcounter="{GOATCOUNTER}" async src="//gc.zgo.at/count.js"></script>' if GOATCOUNTER else ''
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{TITLE}</title>'
            f'<link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="apple-touch-icon.png">'
            f'<meta name="apple-mobile-web-app-title" content="수원 아이랑"><meta name="theme-color" content="#f0b400">'
            f'<style>{CSS}</style></head><body>'
            f'<header class="top"><div class="wrap"><h1>{TITLE}</h1>{week_line}</div></header>{nav}'
            f'<main class="wrap">{body}</main>'
            f'<footer class="wrap">마지막 갱신 {updated:%Y-%m-%d %H:%M} · 출처: {SOURCES}</footer>'
            f'<script>{JS}</script>{stats}</body></html>')
