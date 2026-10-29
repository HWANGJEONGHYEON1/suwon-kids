import io
import json
import unittest
import urllib.error
from unittest import mock

from suwon_kids import ai

OK = json.dumps({'candidates': [{'content': {'parts': [{'text': ' 답 '}]}}]}).encode()


def err(code):
    return urllib.error.HTTPError('u', code, 'x', None, io.BytesIO(b''))


class GenerateTest(unittest.TestCase):
    def run_with(self, results):
        slept = []
        it = iter(results)

        def urlopen(req, timeout):
            r = next(it)
            if isinstance(r, Exception):
                raise r
            return io.BytesIO(r)
        with mock.patch.object(ai, 'env', return_value={'GEMINI_API_KEY': 'k'}), \
                mock.patch.object(ai.urllib.request, 'urlopen', side_effect=urlopen):
            return ai.generate('p', sleep=slept.append), slept

    def test_retries_429_then_ok(self):
        out, slept = self.run_with([err(429), err(503), OK])
        self.assertEqual((out, slept), ('답', list(ai.RETRY_WAITS)))

    def test_gives_up_after_waits(self):
        with self.assertRaises(ai.AIError) as c:
            self.run_with([err(429)] * (len(ai.RETRY_WAITS) + 1))
        self.assertEqual(str(c.exception), 'HTTP 429')

    def test_other_errors_not_retried(self):
        with self.assertRaises(ai.AIError):
            self.run_with([err(400)])


if __name__ == '__main__':
    unittest.main()
