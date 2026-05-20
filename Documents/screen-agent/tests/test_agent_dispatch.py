"""
TDD — RED phase: tests for a shared dispatch_actions helper in agent.py.

Issue: _verify_results duplicates the action dispatch loop from _run_cycle
but misses the diff-edit path for mode='code'. Fixing this requires extracting
a shared dispatch_actions(actions, plan, w, h) function used by both callers.
"""

import sys
import os
import types
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Stub every heavy import so agent.py can be imported without hardware ──────

def _make_stubs():
    # pynput
    pynput_mod   = types.ModuleType('pynput')
    keyboard_mod = types.ModuleType('pynput.keyboard')
    keyboard_mod.GlobalHotKeys = mock.MagicMock()
    pynput_mod.keyboard = keyboard_mod
    sys.modules.setdefault('pynput', pynput_mod)
    sys.modules.setdefault('pynput.keyboard', keyboard_mod)

    # pyautogui
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

    # gi / GTK
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

    # mss / Pillow
    mss_mod = types.ModuleType('mss')
    sys.modules.setdefault('mss', mss_mod)
    pil_mod = types.ModuleType('PIL')
    img_mod = types.ModuleType('PIL.Image')
    img_mod.LANCZOS = 1
    pil_mod.Image   = img_mod
    sys.modules.setdefault('PIL', pil_mod)
    sys.modules.setdefault('PIL.Image', img_mod)

    # dotenv
    dotenv_mod = types.ModuleType('dotenv')
    dotenv_mod.load_dotenv = mock.MagicMock()
    sys.modules.setdefault('dotenv', dotenv_mod)

    # anthropic
    anth_mod = types.ModuleType('anthropic')
    anth_mod.Anthropic       = mock.MagicMock()
    anth_mod.APIStatusError  = Exception
    anth_mod.RateLimitError  = Exception
    sys.modules.setdefault('anthropic', anth_mod)

    # sibling modules
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

    # If agent was already imported by another test file, re-point its bindings
    # to the stubs created here so mock assertions work correctly.
    if 'agent' in sys.modules:
        sys.modules['agent'].act = act_mod
        sys.modules['agent'].ed  = ed_mod

    return act_mod, ed_mod


_act_stub, _edit_stub = _make_stubs()


with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
    import importlib
    import agent as _agent_module


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDispatchActionsExists:
    def test_dispatch_actions_is_callable(self):
        assert callable(getattr(_agent_module, 'dispatch_actions', None)), (
            "dispatch_actions() does not exist in agent.py — "
            "extract it from _run_cycle/_verify_results"
        )


class TestDispatchActionsTextMode:
    def setup_method(self):
        _agent_module.act = _act_stub
        _act_stub.type_text.reset_mock()
        _act_stub.think_pause.reset_mock()
        _agent_module._abort.clear()

    def test_text_mode_calls_type_text(self):
        fn = getattr(_agent_module, 'dispatch_actions', None)
        if fn is None:
            return
        fn([{'type': 'type', 'text': 'hello', 'mode': 'text'}], {}, 1920, 1080)
        _act_stub.type_text.assert_called_once()


class TestDispatchActionsCodeMode:
    def setup_method(self):
        _agent_module.act = _act_stub
        _agent_module.ed  = _edit_stub
        _act_stub.type_text.reset_mock()
        _act_stub.think_pause.reset_mock()
        _edit_stub.diff_actions.reset_mock()
        _agent_module._abort.clear()

    def test_code_mode_with_existing_code_uses_diff_path(self):
        """Core regression: code mode + existing_code must route to diff edits."""
        fn = getattr(_agent_module, 'dispatch_actions', None)
        if fn is None:
            return
        actions = [{'type': 'type', 'text': 'def foo(): pass', 'mode': 'code'}]
        plan    = {'existing_code': 'def foo():\n    return None\n'}
        fn(actions, plan, 1920, 1080)
        _edit_stub.diff_actions.assert_called_once()

    def test_code_mode_without_existing_code_falls_back_to_type_text(self):
        fn = getattr(_agent_module, 'dispatch_actions', None)
        if fn is None:
            return
        fn([{'type': 'type', 'text': 'def foo(): pass', 'mode': 'code'}], {}, 1920, 1080)
        _act_stub.type_text.assert_called_once()


class TestVerifyResultsUsesSharedDispatch:
    def test_verify_results_delegates_to_dispatch_actions(self):
        import inspect
        src = inspect.getsource(_agent_module._verify_results)
        has_inline_loop = 'for step in actions' in src
        has_delegation  = 'dispatch_actions' in src
        assert not has_inline_loop or has_delegation, (
            "_verify_results still contains an inline 'for step in actions' loop "
            "without calling dispatch_actions — the shared helper must be extracted"
        )
