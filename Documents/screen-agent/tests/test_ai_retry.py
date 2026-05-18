"""
TDD — RED phase: tests for retry behaviour in ai.py.

Issue: _get_code (Sonnet call) has no retry — a transient 500 crashes the cycle.
_call retries on 500 but _get_code does not.
"""

import sys
import os
import types
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Minimal stubs so ai.py imports cleanly ────────────────────────────────────

def _stub_anthropic():
    class FakeAPIStatusError(Exception):
        def __init__(self, msg, status_code=500):
            super().__init__(msg)
            self.status_code = status_code

    anth = types.ModuleType('anthropic')
    anth.Anthropic        = mock.MagicMock()
    anth.APIStatusError   = FakeAPIStatusError
    anth.RateLimitError   = type('RateLimitError', (Exception,), {})
    sys.modules['anthropic'] = anth
    return anth, FakeAPIStatusError


_anth_stub, FakeAPIStatusError = _stub_anthropic()

# Force-import the real ai module even if another test file already stubbed it.
import importlib
sys.modules.pop('ai', None)
ai = importlib.import_module('ai')


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGetCodeRetries:
    """_get_code must retry on transient 500 errors, not crash immediately."""

    def setup_method(self):
        ai._client = None

    def _make_client(self, side_effects):
        client = mock.MagicMock()
        client.messages.create.side_effect = side_effects
        ai._client = client
        return client

    def _good_response(self, code='def solution(): pass'):
        resp = mock.MagicMock()
        resp.content = [mock.MagicMock(text=code)]
        return resp

    def test_get_code_returns_code_on_first_try(self):
        self._make_client([self._good_response('def ok(): pass')])
        result = ai._get_code('b64data', 1920, 1080)
        assert result == 'def ok(): pass'

    def test_get_code_retries_once_on_500(self):
        err = FakeAPIStatusError('Internal Server Error', status_code=500)
        self._make_client([err, self._good_response('def ok(): pass')])
        result = ai._get_code('b64data', 1920, 1080)
        assert result == 'def ok(): pass'

    def test_get_code_retries_twice_on_500(self):
        err = FakeAPIStatusError('Internal Server Error', status_code=500)
        self._make_client([err, err, self._good_response('def ok(): pass')])
        result = ai._get_code('b64data', 1920, 1080)
        assert result == 'def ok(): pass'

    def test_get_code_raises_after_three_500s(self):
        err = FakeAPIStatusError('Internal Server Error', status_code=500)
        self._make_client([err, err, err])
        try:
            ai._get_code('b64data', 1920, 1080)
            assert False, "_get_code should have raised after 3 consecutive 500s"
        except Exception:
            pass

    def test_get_code_does_not_retry_non_500_errors(self):
        err = FakeAPIStatusError('Bad Request', status_code=400)
        client = self._make_client([err])
        try:
            ai._get_code('b64data', 1920, 1080)
            assert False, "_get_code should have raised on a 400"
        except Exception:
            pass
        assert client.messages.create.call_count == 1, (
            "_get_code retried a non-500 error — it should not"
        )


class TestIscodingSignals:
    """_is_coding should not over-trigger on weak signals."""

    def test_coding_detected_on_strong_signal(self):
        result = {'context': 'I see a code editor with a function implementation', 'actions': []}
        assert ai._is_coding(result) is True

    def test_coding_not_detected_on_just_python_word(self):
        result = {'context': 'The page mentions Python version 3.11 release notes', 'actions': []}
        assert ai._is_coding(result) is False, (
            "_is_coding triggered on 'python' alone — signal matching is too broad"
        )
