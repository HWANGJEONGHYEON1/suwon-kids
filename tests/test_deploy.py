import tempfile
import unittest
from datetime import date
from pathlib import Path

import deploy


class DeployTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / 'site').mkdir()
        self.git_calls = []

    def git(self, *args):
        self.git_calls.append(args)
        return 1 if args[:2] == ('diff', '--cached') else 0  # 1 = 바뀐 것 있음

    def build_ok(self, today, out_dir, sources=None):
        (out_dir / 'index.html').write_text('<h1>ok</h1>')
        (out_dir / 'events.json').write_text('{}')
        return {'ok': True, 'counts': {}, 'errors': {}}

    def test_ok_copies_to_root_and_pushes(self):
        code = deploy.main(date(2026, 10, 26), self.root, build=self.build_ok, git=self.git, extras={})
        self.assertEqual(code, 0)
        self.assertEqual((self.root / 'index.html').read_text(), '<h1>ok</h1>')
        self.assertTrue((self.root / 'events.json').exists())
        self.assertIn(('commit', '-q', '-m', 'data: 2026-10-26'), self.git_calls)
        self.assertEqual(self.git_calls[-1], ('push', '-q', 'origin', 'main'))

    def test_failure_no_git(self):
        code = deploy.main(date(2026, 10, 26), self.root, build=lambda *a, **k: {'ok': False, 'errors': {'all': 'x'}}, git=self.git, extras={})
        self.assertEqual(code, 1)
        self.assertEqual(self.git_calls, [])
        self.assertTrue(any(self.root.joinpath('logs').iterdir()))

    def test_nothing_changed_no_commit(self):
        calls = []
        code = deploy.main(date(2026, 10, 26), self.root, build=self.build_ok, git=lambda *a: calls.append(a) or 0, extras={})
        self.assertEqual(code, 0)
        self.assertFalse(any(c[0] == 'commit' for c in calls))

    def test_extras_run_and_failure_only_logged(self):
        calls = []

        def boom(t):
            raise RuntimeError('x')
        today = date(2026, 10, 26)
        code = deploy.main(today, self.root, build=self.build_ok, git=self.git,
                           extras={'festivals': lambda t: calls.append(t) or 3, 'bad': boom})
        self.assertEqual(code, 0)
        self.assertEqual(calls, [today])
        log = (self.root / 'logs' / f'build-{today}.log').read_text(encoding='utf-8')
        self.assertIn('"festivals": 3', log)
        self.assertIn('RuntimeError: x', log)

    def test_extras_run_even_if_build_fails(self):
        calls = []
        today = date(2026, 10, 26)
        code = deploy.main(today, self.root, build=lambda *a, **k: {'ok': False, 'errors': {'all': 'x'}},
                           git=self.git, extras={'festivals': calls.append})
        self.assertEqual(code, 1)
        self.assertEqual(calls, [today])


if __name__ == '__main__':
    unittest.main()
