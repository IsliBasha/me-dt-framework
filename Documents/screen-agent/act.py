"""
Human-like action execution: variable-WPM typing, natural mouse movement, click delays.
"""

import random
import subprocess
import time
import pyautogui
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

pyautogui.PAUSE = 0          # disable pyautogui's built-in 0.1 s pause
pyautogui.FAILSAFE = True    # move mouse to top-left corner to abort

QWERTY_ADJACENT: dict[str, list[str]] = {
    'q': ['w', 'a'],    'w': ['q', 'e', 's'],   'e': ['w', 'r', 'd'],
    'r': ['e', 't', 'f'], 't': ['r', 'y', 'g'], 'y': ['t', 'u', 'h'],
    'u': ['y', 'i', 'j'], 'i': ['u', 'o', 'k'], 'o': ['i', 'p', 'l'],
    'p': ['o'],
    'a': ['q', 's'],    's': ['a', 'd', 'w'],    'd': ['s', 'f', 'e'],
    'f': ['d', 'g', 'r'], 'g': ['f', 'h', 't'],  'h': ['g', 'j', 'y'],
    'j': ['h', 'k', 'u'], 'k': ['j', 'l', 'i'],  'l': ['k', 'o'],
    'z': ['a', 'x'],    'x': ['z', 'c', 's'],    'c': ['x', 'v', 'd'],
    'v': ['c', 'b', 'f'], 'b': ['v', 'n', 'g'],  'n': ['b', 'm', 'h'],
    'm': ['n', 'j'],
}

# X11 keysym names for characters pyautogui.write() mangles on Linux
_KEYSYM: dict[str, str] = {
    '<': 'less',          '>': 'greater',
    '{': 'braceleft',     '}': 'braceright',
    '[': 'bracketleft',   ']': 'bracketright',
    '(': 'parenleft',     ')': 'parenright',
    '!': 'exclam',        '@': 'at',
    '#': 'numbersign',    '$': 'dollar',
    '%': 'percent',       '^': 'asciicircum',
    '&': 'ampersand',     '*': 'asterisk',
    '_': 'underscore',    '+': 'plus',
    '|': 'bar',           '~': 'asciitilde',
    '?': 'question',      '"': 'quotedbl',
    ':': 'colon',         '\\': 'backslash',
    '`': 'grave',
}


def _xdo_key(keysym: str) -> None:
    subprocess.run(['xdotool', 'key', '--clearmodifiers', keysym],
                   check=False, capture_output=True)


def _char_delay(wpm: int) -> float:
    base = 60.0 / (wpm * 5)
    return max(0.025, base + random.gauss(0, base * 0.15))


def type_text(text: str, wpm: int = 72, error_rate: float = 0.03) -> None:
    """Type text character by character with burst rhythm and optional typos."""
    burst_left = 0

    for char in text:
        # Burst pause: type 4–9 chars fast, then pause 80–250 ms
        if burst_left <= 0:
            burst_left = random.randint(4, 9)
            time.sleep(random.uniform(0.08, 0.25))
        burst_left -= 1

        if char == '\n':
            pyautogui.press('return')
            time.sleep(random.uniform(0.10, 0.35))
            burst_left = 0
            continue
        if char == '\t':
            pyautogui.press('tab')
            time.sleep(_char_delay(wpm))
            continue

        # Occasional typo on alphabetic chars only
        if char.isalpha() and random.random() < error_rate:
            neighbours = QWERTY_ADJACENT.get(char.lower())
            if neighbours:
                pyautogui.press(random.choice(neighbours))
                time.sleep(_char_delay(wpm) * 0.5)
                pyautogui.hotkey('backspace')
                time.sleep(_char_delay(wpm) * 0.3)

        if char in _KEYSYM:
            _xdo_key(_KEYSYM[char])
        else:
            pyautogui.write(char, interval=0)
        time.sleep(_char_delay(wpm))


def click_at(x_pct: float, y_pct: float, screen_w: int, screen_h: int,
             description: str = '') -> None:
    """
    Move to (x_pct, y_pct) relative screen position and click.
    Adds natural mouse arc and pre-click hesitation.
    """
    px = min(screen_w - 1, max(0, round(x_pct * screen_w)))
    py = min(screen_h - 1, max(0, round(y_pct * screen_h)))

    duration = random.uniform(0.12, 0.35)
    pyautogui.moveTo(px, py, duration=duration, tween=pyautogui.easeInOutQuad)
    time.sleep(random.uniform(0.06, 0.18))
    pyautogui.click()

    if description:
        print(f"    clicked '{description}' @ ({px}, {py})")


def paste_code(code: str) -> None:
    """
    Copy code to GTK clipboard then Ctrl+V — handles every character
    regardless of keyboard layout. Used for code where pyautogui.write()
    mangles angle brackets, generics, or non-ASCII chars.
    """
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clipboard.set_text(code, -1)
    clipboard.store()
    # Brief pause so clipboard settles before paste
    time.sleep(random.uniform(0.15, 0.30))
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(random.uniform(0.10, 0.20))


def think_pause(lo: float = 0.5, hi: float = 2.0) -> None:
    """Simulate reading/thinking before acting."""
    time.sleep(random.uniform(lo, hi))
