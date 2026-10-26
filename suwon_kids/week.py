"""이번 주 = 오늘 ~ 그 주 일요일. 30일 넘는 행사는 '상시'."""
from datetime import date, timedelta

from suwon_kids.models import Event

LONG_DAYS = 30


def this_week(today: date) -> tuple[date, date]:
    return today, today + timedelta(days=6 - today.weekday())


def overlaps(ev: Event, rng: tuple[date, date]) -> bool:
    return ev.start <= rng[1] and ev.end >= rng[0]


def is_long(ev: Event) -> bool:
    return (ev.end - ev.start).days > LONG_DAYS
