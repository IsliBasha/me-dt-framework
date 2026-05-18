"""Tests for diff-based targeted line editing (edit.py — new module).

Called by: pytest from project root. edit.py does not exist yet (RED phase).
No existing test_edit.py found. No data files — pure function tests.
User instruction: "make the script type it humanely without ctrl a deleting it all and starting from the begining"
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

sys.modules.pop('edit', None)  # clear any stub registered by other test files
import edit


def test_identical_code_no_actions():
    code = "def foo():\n    return 1\n"
    assert edit.diff_actions(code, code) == []


def test_single_line_change():
    old = "def foo():\n    return 1\n"
    new = "def foo():\n    return 2\n"
    actions = edit.diff_actions(old, new)
    assert len(actions) == 1
    assert actions[0]['line'] == 2


def test_action_has_new_text():
    old = "x = 1\n"
    new = "x = 42\n"
    actions = edit.diff_actions(old, new)
    assert actions[0]['text'] == "x = 42"


def test_multiline_replace():
    old = "a\nb\nc\n"
    new = "a\nX\nY\nc\n"
    actions = edit.diff_actions(old, new)
    assert len(actions) == 1
    assert actions[0]['line'] == 2
    assert actions[0]['select_lines'] == 1


def test_insert_at_top():
    old = "b\nc\n"
    new = "a\nb\nc\n"
    actions = edit.diff_actions(old, new)
    assert len(actions) == 1
    assert actions[0]['line'] == 1


def test_delete_lines():
    old = "a\nb\nc\n"
    new = "a\nc\n"
    actions = edit.diff_actions(old, new)
    assert len(actions) == 1
    assert actions[0]['text'] == ""
