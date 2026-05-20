"""Tests for the abort / kill-switch feature in agent.py.

Press ABORT_HOTKEY (default Ctrl+Alt+X) mid-cycle to stop dispatch immediately.
"""

import sys
import os
import types
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Stubs (mirrors test_agent_dispatch.py) ────────────────────────────────────

def _make_stubs():
    pynput_mod   = types.ModuleType('pynput')
    keyboard_mod = types.ModuleType('pynput.keyboard')
    keyboard_mod.GlobalHotKeys = mock.MagicMock()
    pynput_mod.keyboard = keyboard_mod
    sys.modules.setdefault('pynput', pynput_mod)
    sys.modules.setdefault('pynput.keyboard', keyboard_mod)

    pag = types.ModuleType('pyautogui')
    pag.PAUSE    = 0
    pag.FAILSAFE = True
    pag.hotkey   = mock.MagicMock()
    pag.press    = mock.MagicMock()
    pag.write    = mock.MagicMock()
    pag.moveTo   = mock.MagicMock()
    pag.click    = mock.MagicMock()
    pag.easeInOutQuad = lambda t: t
    sys.modules.setdefault('pyautogui', pag)

    gi_mod  = types.ModuleType('gi')
    gi_mod.require_version = mock.MagicMock()
    repo_mod = types.ModuleType('gi.repository')
    gtk_mod  = types.ModuleType('gi.repository.Gtk')
    gdk_mod  = types.ModuleType('gi.repository.Gdk')
    repo_mod.Gtk = gtk_mod
    repo_mod.Gdk = gdk_mod
    sys.modules.setdefault('gi', gi_mod)
    sys.modules.setdefault('gi.repository', repo_mod)
    sys.modules.setdefault('gi.repository.Gtk', gtk_mod)
    sys.modules.setdefault('gi.repository.Gdk', gdk_mod)

    mss_mod = types.ModuleType('mss')
    sys.modules.setdefault('mss', mss_mod)
    pil_mod = types.ModuleType('PIL')
    img_mod = types.ModuleType('PIL.Image')
    img_mod.LANCZOS = 1
    pil_mod.Image   = img_mod
    sys.modules.setdefault('PIL', pil_mod)
    sys.modules.setdefault('PIL.Image', img_mod)

    dotenv_mod = types.ModuleType('dotenv')
    dotenv_mod.load_dotenv = mock.MagicMock()
    sys.modules.setdefault('dotenv', dotenv_mod)

    anth_mod = types.ModuleType('anthropic')
    anth_mod.Anthropic       = mock.MagicMock()
    anth_mod.APIStatusError  = Exception
    anth_mod.RateLimitError  = Exception
    sys.modules.setdefault('anthropic', anth_mod)

    act_mod = types.ModuleType('act')
    act_mod.type_text   = mock.MagicMock()
    act_mod.click_at    = mock.MagicMock()
    act_mod.think_pause = mock.MagicMock()
    act_mod.paste_code  = mock.MagicMock()
    sys.modules['act'] = act_mod

    ai_mod = types.ModuleType('ai')
    ai_mod.analyze       = mock.MagicMock()
    ai_mod.HAIKU_MODEL   = 'haiku'
    ai_mod.SONNET_MODEL  = 'sonnet'
    sys.modules['ai'] = ai_mod

    sc_mod = types.ModuleType('screen')
    sc_mod.capture    = mock.MagicMock(return_value=(b'', 1920, 1080))
    sc_mod.to_base64  = mock.MagicMock(return_value='')
    sys.modules['screen'] = sc_mod

    ed_mod = types.ModuleType('edit')
    ed_mod.diff_actions = mock.MagicMock(return_value=[])
    sys.modules['edit'] = ed_mod

    return act_mod


_act_stub = _make_stubs()

with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
    import importlib
    import agent as _agent_module


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestAbortEventExists:
    def test_abort_is_threading_event(self):
        import threading
        assert hasattr(_agent_module, '_abort'), "_abort not found in agent"
        assert isinstance(_agent_module._abort, threading.Event)

    def test_abort_hotkey_env_var_used(self):
        assert hasattr(_agent_module, 'ABORT_HOTKEY'), "ABORT_HOTKEY not defined"

    def test_abort_hotkey_default(self):
        assert '<ctrl>+<alt>+x' in _agent_module.ABORT_HOTKEY.lower() or \
               'ctrl' in _agent_module.ABORT_HOTKEY.lower(), \
               "ABORT_HOTKEY should default to a ctrl combo"


class TestDispatchActionsAbortsCleanly:
    def setup_method(self):
        _agent_module.act = _act_stub  # ensure agent uses this file's stub
        _act_stub.type_text.reset_mock()
        _act_stub.think_pause.reset_mock()
        _agent_module._abort.clear()

    def test_dispatch_runs_normally_when_not_aborted(self):
        actions = [
            {'type': 'type', 'text': 'hello', 'mode': 'text'},
            {'type': 'type', 'text': 'world', 'mode': 'text'},
        ]
        _agent_module.dispatch_actions(actions, {}, 1920, 1080)
        assert _act_stub.type_text.call_count == 2

    def test_dispatch_stops_when_abort_set_before_call(self):
        _agent_module._abort.set()
        actions = [
            {'type': 'type', 'text': 'should not run', 'mode': 'text'},
        ]
        _agent_module.dispatch_actions(actions, {}, 1920, 1080)
        _act_stub.type_text.assert_not_called()

    def test_dispatch_stops_mid_sequence_when_abort_set(self):
        call_count = [0]
        original = _act_stub.type_text.side_effect

        def set_abort_on_second(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 1:
                _agent_module._abort.set()

        _act_stub.type_text.side_effect = set_abort_on_second

        actions = [
            {'type': 'type', 'text': 'first',  'mode': 'text'},
            {'type': 'type', 'text': 'second', 'mode': 'text'},
            {'type': 'type', 'text': 'third',  'mode': 'text'},
        ]
        _agent_module.dispatch_actions(actions, {}, 1920, 1080)

        # First action runs, then abort is detected — second and third skipped
        assert _act_stub.type_text.call_count < 3

        _act_stub.type_text.side_effect = original


class TestRunCycleClearsAbort:
    def test_run_cycle_clears_abort_at_start(self):
        """Each new Ctrl+Alt+G cycle should reset the abort flag."""
        _agent_module._abort.set()

        _agent_module.sc.capture.return_value = (b'', 1920, 1080)
        _agent_module.ai.analyze.return_value = {'context': 'nothing', 'actions': []}

        _agent_module._run_cycle()

        assert not _agent_module._abort.is_set(), \
            "_run_cycle must clear _abort at the start of each cycle"

    def test_run_cycle_stops_before_dispatch_if_abort_set_during_ai_call(self):
        """Abort pressed while Claude is thinking must prevent any action from firing."""
        _agent_module._abort.clear()
        _act_stub.click_at.reset_mock()
        _agent_module.act = _act_stub

        def ai_sets_abort(*args, **kwargs):
            _agent_module._abort.set()
            return {'context': 'test', 'actions': [
                {'type': 'click', 'x_pct': 0.5, 'y_pct': 0.5, 'description': 'btn'}
            ]}

        _agent_module.sc.capture.return_value = (b'', 1920, 1080)
        _agent_module.ai.analyze.side_effect = ai_sets_abort
        _agent_module._run_cycle()
        _agent_module.ai.analyze.side_effect = None

        _act_stub.click_at.assert_not_called()


class TestDispatchWaitIsInterruptible:
    def setup_method(self):
        _agent_module.act = _act_stub
        _agent_module._abort.clear()

    def test_wait_action_exits_early_on_abort(self):
        """A long wait action must return quickly when abort is set mid-sleep."""
        import threading, time

        actions = [{'type': 'wait', 'seconds': 10.0}]
        threading.Timer(0.05, _agent_module._abort.set).start()

        start = time.monotonic()
        _agent_module.dispatch_actions(actions, {}, 1920, 1080)
        elapsed = time.monotonic() - start

        assert elapsed < 1.0, f"wait took {elapsed:.2f}s — should have aborted in <1s"
