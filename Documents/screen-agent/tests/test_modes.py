"""
TDD — RED phase: tests for two distinct hotkey modes.

Click mode (Ctrl+Alt+G): only dispatches click/wait actions.
Type  mode (Ctrl+Alt+T): only dispatches type/key/wait actions.
Both modes share the same Ctrl+Alt+X abort hotkey.
"""

import sys
import os
import types
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Stubs (same pattern as test_agent_dispatch.py) ────────────────────────────

def _ensure(name: str, **attrs) -> types.ModuleType:
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
    return sys.modules[name]


pynput_mod   = _ensure('pynput')
keyboard_mod = _ensure('pynput.keyboard', GlobalHotKeys=mock.MagicMock())
pynput_mod.keyboard = keyboard_mod

pag = _ensure('pyautogui',
              PAUSE=0, FAILSAFE=True,
              hotkey=mock.MagicMock(), press=mock.MagicMock(),
              write=mock.MagicMock(), moveTo=mock.MagicMock(),
              click=mock.MagicMock(), easeInOutQuad=lambda t: t)

gi_mod   = _ensure('gi', require_version=mock.MagicMock())
repo_mod = _ensure('gi.repository')
gtk_mod  = _ensure('gi.repository.Gtk')
gdk_mod  = _ensure('gi.repository.Gdk')
repo_mod.Gtk = gtk_mod
repo_mod.Gdk = gdk_mod

_ensure('mss')
pil_mod      = _ensure('PIL')
img_mod      = _ensure('PIL.Image', LANCZOS=1)
pil_mod.Image = img_mod

_ensure('dotenv', load_dotenv=mock.MagicMock())
_ensure('anthropic',
        Anthropic=mock.MagicMock(),
        APIStatusError=Exception,
        RateLimitError=Exception)

_act_stub = _ensure('act',
                    type_text=mock.MagicMock(),
                    click_at=mock.MagicMock(),
                    think_pause=mock.MagicMock(),
                    paste_code=mock.MagicMock())
_ai_stub  = _ensure('ai',
                    analyze=mock.MagicMock(return_value={'context': 'test', 'actions': []}),
                    HAIKU_MODEL='haiku',
                    SONNET_MODEL='sonnet')
_sc_stub  = _ensure('screen',
                    capture=mock.MagicMock(return_value=(b'', 1920, 1080)),
                    to_base64=mock.MagicMock(return_value=''),
                    MAX_LONG_EDGE=1280)
_ed_stub  = _ensure('edit', diff_actions=mock.MagicMock(return_value=[]))

with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
    import agent as _ag


def _reset():
    # Reassign fresh MagicMocks — other test files may have swapped in real functions.
    _act_stub.type_text   = mock.MagicMock()
    _act_stub.click_at    = mock.MagicMock()
    _act_stub.think_pause = mock.MagicMock()
    _act_stub.paste_code  = mock.MagicMock()
    _ai_stub.analyze      = mock.MagicMock(return_value={'context': 'test', 'actions': []})
    pag.hotkey            = mock.MagicMock()
    _ag._abort.clear()
    _ag.act = _act_stub
    _ag.ai  = _ai_stub
    _ag.sc  = _sc_stub


# ── Hotkey constants ───────────────────────────────────────────────────────────

class TestHotkeyConstants:
    def test_click_hotkey_exists(self):
        assert hasattr(_ag, 'CLICK_HOTKEY'), \
            "CLICK_HOTKEY constant missing from agent.py"

    def test_type_hotkey_exists(self):
        assert hasattr(_ag, 'TYPE_HOTKEY'), \
            "TYPE_HOTKEY constant missing from agent.py"

    def test_type_hotkey_default_is_ctrl_alt_t(self):
        assert 't' in _ag.TYPE_HOTKEY.lower(), \
            f"TYPE_HOTKEY should default to Ctrl+Alt+T, got {_ag.TYPE_HOTKEY!r}"

    def test_click_hotkey_default_is_ctrl_alt_g(self):
        assert 'g' in _ag.CLICK_HOTKEY.lower(), \
            f"CLICK_HOTKEY should default to Ctrl+Alt+G, got {_ag.CLICK_HOTKEY!r}"


# ── dispatch_actions — click mode ──────────────────────────────────────────────

class TestDispatchClickMode:
    def setup_method(self):
        _reset()

    def test_skips_type_actions(self):
        _ag.dispatch_actions(
            [{'type': 'type', 'text': 'hello', 'mode': 'text'}],
            {}, 1920, 1080, mode='click',
        )
        _act_stub.type_text.assert_not_called()

    def test_skips_key_actions(self):
        _ag.dispatch_actions(
            [{'type': 'key', 'key': 'Return'}],
            {}, 1920, 1080, mode='click',
        )
        pag.hotkey.assert_not_called()

    def test_executes_click_actions(self):
        _ag.dispatch_actions(
            [{'type': 'click', 'x_pct': 0.5, 'y_pct': 0.5, 'description': 'btn'}],
            {}, 1920, 1080, mode='click',
        )
        _act_stub.click_at.assert_called_once()

    def test_executes_wait_actions(self):
        _ag.dispatch_actions(
            [{'type': 'wait', 'seconds': 0.01}],
            {}, 1920, 1080, mode='click',
        )


# ── dispatch_actions — type mode ───────────────────────────────────────────────

class TestDispatchTypeMode:
    def setup_method(self):
        _reset()

    def test_skips_click_actions(self):
        _ag.dispatch_actions(
            [{'type': 'click', 'x_pct': 0.5, 'y_pct': 0.5, 'description': 'btn'}],
            {}, 1920, 1080, mode='type',
        )
        _act_stub.click_at.assert_not_called()

    def test_executes_type_actions(self):
        _ag.dispatch_actions(
            [{'type': 'type', 'text': 'hello', 'mode': 'text'}],
            {}, 1920, 1080, mode='type',
        )
        _act_stub.type_text.assert_called_once()

    def test_executes_key_actions(self):
        _ag.dispatch_actions(
            [{'type': 'key', 'key': 'Return'}],
            {}, 1920, 1080, mode='type',
        )
        pag.hotkey.assert_called_once()

    def test_executes_wait_actions(self):
        _ag.dispatch_actions(
            [{'type': 'wait', 'seconds': 0.01}],
            {}, 1920, 1080, mode='type',
        )


# ── dispatch_actions — auto mode (default / backward-compat) ──────────────────

class TestDispatchAutoMode:
    def setup_method(self):
        _reset()

    def test_executes_type_actions(self):
        _ag.dispatch_actions(
            [{'type': 'type', 'text': 'hello', 'mode': 'text'}],
            {}, 1920, 1080,
        )
        _act_stub.type_text.assert_called_once()

    def test_executes_click_actions(self):
        _ag.dispatch_actions(
            [{'type': 'click', 'x_pct': 0.5, 'y_pct': 0.5, 'description': 'btn'}],
            {}, 1920, 1080,
        )
        _act_stub.click_at.assert_called_once()

    def test_executes_key_actions(self):
        _ag.dispatch_actions(
            [{'type': 'key', 'key': 'ctrl+a'}],
            {}, 1920, 1080,
        )
        pag.hotkey.assert_called_once()


# ── _run_cycle passes mode to ai.analyze ──────────────────────────────────────

class TestRunCycleModePassthrough:
    def setup_method(self):
        _reset()
        _ai_stub.analyze.return_value = {'context': 'ok', 'actions': []}
        _sc_stub.capture.return_value = (b'', 1920, 1080)

    def test_click_mode_passed_to_analyze(self):
        _ag._run_cycle(mode='click')
        call_args = _ai_stub.analyze.call_args
        passed_mode = call_args.kwargs.get('mode') or (
            call_args.args[3] if len(call_args.args) > 3 else None
        )
        assert passed_mode == 'click', \
            f"ai.analyze() was not called with mode='click', got {call_args}"

    def test_type_mode_passed_to_analyze(self):
        _ag._run_cycle(mode='type')
        call_args = _ai_stub.analyze.call_args
        passed_mode = call_args.kwargs.get('mode') or (
            call_args.args[3] if len(call_args.args) > 3 else None
        )
        assert passed_mode == 'type', \
            f"ai.analyze() was not called with mode='type', got {call_args}"

    def test_click_mode_prevents_type_actions_from_dispatch(self):
        _ai_stub.analyze.return_value = {
            'context': 'ok',
            'actions': [{'type': 'type', 'text': 'bad', 'mode': 'text'}],
        }
        _ag._run_cycle(mode='click')
        _act_stub.type_text.assert_not_called()

    def test_type_mode_prevents_click_actions_from_dispatch(self):
        _ai_stub.analyze.return_value = {
            'context': 'ok',
            'actions': [{'type': 'click', 'x_pct': 0.5, 'y_pct': 0.5, 'description': 'x'}],
        }
        _ag._run_cycle(mode='type')
        _act_stub.click_at.assert_not_called()


# ── ai.analyze accepts mode kwarg ─────────────────────────────────────────────

def _load_real_ai():
    """Load the real ai.py from disk, bypassing the sys.modules stub."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        '_ai_real',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ai.py'),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestAiAnalyzeModeInterface:
    def setup_method(self):
        self.ai_real = _load_real_ai()

    def test_analyze_mode_kwarg_accepted(self):
        """ai.analyze() must accept a mode keyword argument without raising."""
        import inspect
        sig = inspect.signature(self.ai_real.analyze)
        assert 'mode' in sig.parameters, \
            "ai.analyze() is missing the 'mode' parameter"

    def test_messages_payload_click_mode_contains_hint(self):
        """_messages_payload with mode='click' must include click-only instruction."""
        payload = self.ai_real._messages_payload('data', 1366, 768, mode='click')
        text = payload[0]['content'][1]['text'].lower()
        assert 'click' in text and ('only' in text or 'mode' in text), \
            f"click mode hint missing from message payload: {text!r}"

    def test_messages_payload_type_mode_contains_hint(self):
        """_messages_payload with mode='type' must include type-only instruction."""
        payload = self.ai_real._messages_payload('data', 1366, 768, mode='type')
        text = payload[0]['content'][1]['text'].lower()
        assert 'type' in text and ('only' in text or 'mode' in text), \
            f"type mode hint missing from message payload: {text!r}"

    def test_messages_payload_auto_mode_has_no_restriction(self):
        """_messages_payload in auto mode must not add a mode restriction."""
        payload = self.ai_real._messages_payload('data', 1366, 768, mode='auto')
        text = payload[0]['content'][1]['text'].lower()
        assert 'only' not in text, \
            f"auto mode should not restrict action types, got: {text!r}"
