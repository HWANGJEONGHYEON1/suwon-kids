"""매일 실행: 빌드 → site/ 를 저장소 루트로 복사(GitHub Pages는 루트만) → 바뀐 게 있으면 커밋·푸시.
빌드가 실패하면 커밋하지 않고 logs/build-YYYY-MM-DD.log 에 남긴다. launchd 가 python 으로 직접 부른다."""
import json
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PUBLISHED = ('index.html', 'events.json')


def _git(*args) -> int:
    return subprocess.run(['git', *args], cwd=ROOT).returncode


def _log(root: Path, today: date, text: str):
    (root / 'logs').mkdir(exist_ok=True)
    with open(root / 'logs' / f'build-{today}.log', 'a', encoding='utf-8') as f:
        f.write(f'{datetime.now():%H:%M:%S} {text}\n')


def main(today: date, root: Path = ROOT, build=None, git=_git) -> int:
    if build is None:
        from suwon_kids.build import run, default_sources
        build = lambda t, out: run(t, out, default_sources())  # noqa: E731
    r = build(today, root / 'site')
    _log(root, today, json.dumps(r, ensure_ascii=False))
    if not r['ok']:
        return 1
    for name in PUBLISHED:
        shutil.copy2(root / 'site' / name, root / name)
    git('add', 'site', 'state', *PUBLISHED)
    if git('diff', '--cached', '--quiet') == 0:
        return 0
    git('commit', '-q', '-m', f'data: {today}')
    return 1 if git('push', '-q', 'origin', 'main') else 0


if __name__ == '__main__':
    sys.exit(main(date.today()))
