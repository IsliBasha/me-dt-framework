"""
Tests for ai.py — model routing by mode and _call retry on transient 500s.
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

import importlib
sys.modules.pop('ai', None)
ai = importlib.import_module('ai')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _good_response(payload='{"context":"ok","actions":[]}'):
    resp = mock.MagicMock()
    resp.content = [mock.MagicMock(text=payload)]
    return resp


def _make_client(side_effects):
    client = mock.MagicMock()
    client.messages.create.side_effect = side_effects
    ai._client = client
    return client


# ── Model routing by mode ─────────────────────────────────────────────────────

class TestModelRouting:
    def setup_method(self):
        ai._client = None

    def test_click_mode_uses_haiku(self):
        client = _make_client([_good_response()])
        ai._call('b64', 1920, 1080, ai.HAIKU_MODEL, mode='click')
        _, kwargs = client.messages.create.call_args
        assert kwargs['model'] == ai.HAIKU_MODEL

    def test_type_mode_uses_sonnet(self):
        client = _make_client([_good_response()])
        ai._call('b64', 1920, 1080, ai.SONNET_MODEL, mode='type')
        _, kwargs = client.messages.create.call_args
        assert kwargs['model'] == ai.SONNET_MODEL

    def test_analyze_routes_haiku_for_click(self):
        screen_stub = types.ModuleType('screen')
        screen_stub.to_base64 = mock.MagicMock(return_value='b64')
        screen_stub.MAX_LONG_EDGE = 1280
        sys.modules['screen'] = screen_stub

        client = _make_client([_good_response()])
        ai.analyze(b'', 1920, 1080, mode='click')
        _, kwargs = client.messages.create.call_args
        assert kwargs['model'] == ai.HAIKU_MODEL

    def test_analyze_routes_sonnet_for_type(self):
        screen_stub = types.ModuleType('screen')
        screen_stub.to_base64 = mock.MagicMock(return_value='b64')
        screen_stub.MAX_LONG_EDGE = 1280
        sys.modules['screen'] = screen_stub

        client = _make_client([_good_response()])
        ai.analyze(b'', 1920, 1080, mode='type')
        _, kwargs = client.messages.create.call_args
        assert kwargs['model'] == ai.SONNET_MODEL

    def test_analyze_routes_haiku_for_auto(self):
        screen_stub = types.ModuleType('screen')
        screen_stub.to_base64 = mock.MagicMock(return_value='b64')
        screen_stub.MAX_LONG_EDGE = 1280
        sys.modules['screen'] = screen_stub

        client = _make_client([_good_response()])
        ai.analyze(b'', 1920, 1080, mode='auto')
        _, kwargs = client.messages.create.call_args
        assert kwargs['model'] == ai.HAIKU_MODEL


# ── _call retry on transient 500s ─────────────────────────────────────────────

class TestCallRetries:
    def setup_method(self):
        ai._client = None

    def test_returns_result_on_first_try(self):
        _make_client([_good_response()])
        result = ai._call('b64', 1920, 1080, ai.HAIKU_MODEL)
        assert result == {'context': 'ok', 'actions': []}

    def test_retries_once_on_500(self):
        err = FakeAPIStatusError('Internal Server Error', status_code=500)
        _make_client([err, _good_response()])
        result = ai._call('b64', 1920, 1080, ai.HAIKU_MODEL)
        assert result['context'] == 'ok'

    def test_retries_twice_on_500(self):
        err = FakeAPIStatusError('Internal Server Error', status_code=500)
        _make_client([err, err, _good_response()])
        result = ai._call('b64', 1920, 1080, ai.HAIKU_MODEL)
        assert result['context'] == 'ok'

    def test_raises_after_three_500s(self):
        err = FakeAPIStatusError('Internal Server Error', status_code=500)
        _make_client([err, err, err])
        try:
            ai._call('b64', 1920, 1080, ai.HAIKU_MODEL)
            assert False, "_call should have raised after 3 consecutive 500s"
        except Exception:
            pass

    def test_does_not_retry_non_500_errors(self):
        err = FakeAPIStatusError('Bad Request', status_code=400)
        client = _make_client([err])
        try:
            ai._call('b64', 1920, 1080, ai.HAIKU_MODEL)
            assert False, "_call should have raised on a 400"
        except Exception:
            pass
        assert client.messages.create.call_count == 1, (
            "_call retried a non-500 error — it should not"
        )
