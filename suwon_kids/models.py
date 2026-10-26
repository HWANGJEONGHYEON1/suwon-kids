from dataclasses import dataclass, asdict
from datetime import date


@dataclass
class Event:
    id: str
    source: str
    title: str
    start: date
    end: date
    time: str | None
    place: str
    address: str
    url: str
    target: str
    host: str | None = None
    summary: str | None = None
    area: str | None = None
    image: str | None = None

    def to_json(self) -> dict:
        d = asdict(self)
        d['start'], d['end'] = self.start.isoformat(), self.end.isoformat()
        return d
