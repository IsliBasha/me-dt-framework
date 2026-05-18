#!/usr/bin/env python3
"""
Screen agent — press Ctrl+Alt+G to snapshot the screen,
ask Claude what to do, then act with human-like timing.

Setup:
    cp .env.example .env
    echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env
    pip install -r requirements.txt
    python agent.py
"""

import os
import sys
import time
import json
import threading

from dotenv import load_dotenv
load_dotenv()

if not os.getenv('ANTHROPIC_API_KEY'):
    print('[!] ANTHROPIC_API_KEY is not set. Add it to .env or export it.')
    sys.exit(1)

from pynput import keyboard
import screen as sc
import ai
import act
import edit as ed

# ── Configuration (override via .env) ─────────────────────────────────────────
# Hotkey: <ctrl>+<alt>+g  (change HOTKEY in .env to any pynput combo string)
HOTKEY       = os.getenv('HOTKEY',       '<ctrl>+<alt>+g')
ABORT_HOTKEY = os.getenv('ABORT_HOTKEY', '<ctrl>+<alt>+x')
WPM          = int(os.getenv('WPM', '72'))
ERROR_RATE   = float(os.getenv('ERROR_RATE', '0.03'))

_busy  = False            # prevent re-entrant captures while acting
_abort = threading.Event()  # set by ABORT_HOTKEY to stop current cycle mid-action

import pyautogui


def _apply_diff_edits(old_code: str, new_code: str, screen_w: int, screen_h: int) -> None:
    """
    Navigate to each changed line using Ctrl+G and retype only the changed sections.
    Looks like a human making targeted edits rather than replacing the whole file.
    """
    actions = ed.diff_actions(old_code, new_code)
    if not actions:
        print('  (no changes needed)')
        return

    for a in actions:
        line_no = a['line']
        select  = a['select_lines']
        text    = a['text']

        print(f'  → edit line {line_no} ({select} lines → "{text[:40]}{"…" if len(text)>40 else ""}")')
        act.think_pause(0.2, 0.6)

        # Navigate to target line via Ctrl+G
        pyautogui.hotkey('ctrl', 'g')
        time.sleep(0.25)
        pyautogui.write(str(line_no), interval=0.05)
        pyautogui.press('return')
        time.sleep(0.15)

        # Select the lines to replace
        pyautogui.press('home')
        if select > 0:
            pyautogui.hotkey('shift', 'down') if select == 1 else None
            for _ in range(select - 1):
                pyautogui.hotkey('shift', 'down')
            pyautogui.hotkey('shift', 'end')
        else:
            # Pure insert — move to line start, press Home then Enter to open a new line above
            pyautogui.press('home')
            pyautogui.hotkey('ctrl', 'shift', 'k')  # delete current line placeholder

        act.think_pause(0.1, 0.3)
        if text:
            act.type_text(text, wpm=WPM, error_rate=0)
        else:
            pyautogui.press('delete')


def _on_activate() -> None:
    global _busy
    if _busy:
        return
    _busy = True
    try:
        _run_cycle()
    finally:
        _busy = False


# ── Main cycle ─────────────────────────────────────────────────────────────────

def _on_abort() -> None:
    _abort.set()
    print('\n[!] Abort requested — stopping after current action.')


def _run_cycle() -> None:
    _abort.clear()
    print('\n[+] Capturing screen...')
    png, w, h = sc.capture()

    print('[+] Asking Claude...')
    try:
        plan = ai.analyze(png, w, h)
    except json.JSONDecodeError as exc:
        print(f'[!] Claude returned invalid JSON: {exc}')
        return
    except Exception as exc:
        print(f'[!] AI error: {exc}')
        return

    context = plan.get('context', '')
    actions = plan.get('actions', [])
    print(f'[+] Context : {context}')
    print(f'[+] Actions : {len(actions)}')

    dispatch_actions(actions, plan, w, h)

    # Auto-verify: if we clicked Run/Submit, re-analyze after a short wait
    ran_tests = any(
        any(word in step.get('description', '').lower()
            for word in ('run', 'test', 'submit', 'check'))
        for step in actions if step.get('type') == 'click'
    )
    if ran_tests:
        print('[+] Waiting for results...')
        time.sleep(5)
        _verify_results()

    print('[+] Done.\n')


def dispatch_actions(actions: list, plan: dict, screen_w: int, screen_h: int) -> None:
    """Execute a list of Claude actions with human-like timing."""
    for step in actions:
        if _abort.is_set():
            print('[!] Aborted.')
            return

        kind = step.get('type', '')

        if kind == 'type':
            text = step.get('text', '')
            if not text:
                continue
            mode    = step.get('mode', 'text')
            preview = text[:60] + ('…' if len(text) > 60 else '')
            print(f'  → type [{mode}]: "{preview}"')
            act.think_pause(0.4, 1.2)
            if mode == 'code':
                existing = plan.get('existing_code', '')
                if existing and existing.strip():
                    print('  (using targeted diff edits)')
                    _apply_diff_edits(existing, text, screen_w, screen_h)
                else:
                    act.type_text(text, wpm=WPM, error_rate=0)
            else:
                act.type_text(text, wpm=WPM, error_rate=ERROR_RATE)

        elif kind == 'click':
            x_pct = float(step.get('x_pct', 0.5))
            y_pct = float(step.get('y_pct', 0.5))
            desc  = step.get('description', '')
            print(f'  → click: {desc} ({x_pct:.2f}, {y_pct:.2f})')
            act.think_pause(0.3, 0.9)
            act.click_at(x_pct, y_pct, screen_w, screen_h, description=desc)

        elif kind == 'key':
            combo = step.get('key', '')
            print(f'  → key: {combo}')
            pyautogui.hotkey(*combo.split('+'))

        elif kind == 'wait':
            seconds = float(step.get('seconds', 1.0))
            print(f'  → wait {seconds:.1f}s')
            time.sleep(seconds)

        else:
            print(f'  → unknown action: {kind!r}')


def _verify_results() -> None:
    """Take a fresh screenshot and report whether tests passed or failed."""
    print('[+] Checking results...')
    png, w, h = sc.capture()
    try:
        result = ai.analyze(png, w, h)
    except Exception as exc:
        print(f'[!] Verify error: {exc}')
        return

    context = result.get('context', '')
    actions = result.get('actions', [])
    print(f'[+] Result  : {context}')

    if actions:
        print(f'[+] Follow-up actions: {len(actions)}')
        dispatch_actions(actions, result, w, h)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    print('Screen agent ready.')
    print(f'  Hotkey  : {HOTKEY}')
    print(f'  WPM     : {WPM}')
    print(f'  Default : {ai.HAIKU_MODEL}')
    print(f'  Coding  : {ai.SONNET_MODEL}')
    print('Press Ctrl+C to exit.\n')

    print(f'  Abort   : {ABORT_HOTKEY}')
    with keyboard.GlobalHotKeys({HOTKEY: _on_activate, ABORT_HOTKEY: _on_abort}) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print('\nExiting.')


if __name__ == '__main__':
    main()
