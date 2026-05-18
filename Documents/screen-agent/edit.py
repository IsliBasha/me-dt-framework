"""
Diff-based targeted line edits — used by agent.py to make surgical code changes
instead of ctrl+a full replacement.

Called by: agent.py (apply_diff_edits), tests/test_edit.py.
No existing edit.py found. No data files — pure functions only.
User instruction: "make the script type it humanely without ctrl a deleting it all and starting from the begining"
"""

import difflib


def diff_actions(old_code: str, new_code: str) -> list[dict]:
    """
    Compute minimal line-level edit actions to transform old_code into new_code.

    Each action:
      {'line': int,           # 1-based line number to navigate to
       'select_lines': int,   # lines to select downward (0 = insert only)
       'text': str}           # replacement text (empty string = delete)
    """
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)

    actions = []
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            continue

        replacement = ''.join(new_lines[j1:j2]).rstrip('\n')
        select = i2 - i1

        actions.append({
            'line': i1 + 1,
            'select_lines': select,
            'text': replacement,
        })

    return actions
