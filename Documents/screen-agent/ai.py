"""
Claude vision — sends a screenshot and returns a structured action plan.
"""

import json
import os
import time
import anthropic

_client: anthropic.Anthropic | None = None

SYSTEM_PROMPT = """\
You are a screen-reading automation agent. Analyze the screenshot and \
return a JSON action plan. Return ONLY valid JSON — no markdown fences, \
no commentary outside the JSON.

Response schema:
{
  "context": "<one sentence: what you see>",
  "actions": [
    {"type": "click",  "x_pct": <0-1>, "y_pct": <0-1>, "description": "<element>"},
    {"type": "type",   "text": "<exact text to type>", "mode": "code|text"},
    {"type": "key",    "key": "<e.g. ctrl+a, ctrl+End, Return>"},
    {"type": "wait",   "seconds": <float>}
  ]
}

x_pct / y_pct are relative positions from the top-left (0.0) to \
bottom-right (1.0) of the IMAGE you received. Base these fractions on \
the image's own pixel dimensions, not the reported screen resolution.

── General rules ────────────────────────────────────────────────────────
- Text inputs / open questions  → "type" the best answer.
- Multiple choice / radio / checkbox → "click" the best option by coords.
- Buttons (Next, Submit, Run, Continue) → "click" after filling fields.
- Nothing actionable visible → {"context": "nothing actionable", "actions": []}

── Coding challenge rules ───────────────────────────────────────────────
When you see a coding challenge, IDE, or code editor on screen:

1. READ the problem statement, constraints, function signature, and examples.

2. Copy the EXACT current code visible in the editor into "existing_code" field.

3. Use this action sequence — NO ctrl+a, targeted edits only:
   a. "click"  the code editor body to focus it
   b. "type"   with "text": "<<CODE>>", "mode": "code"
      (the corrected code will be injected and diffed against existing_code)
   c. "wait"   0.5
   d. "click"  the Run Tests / Submit button

4. After clicking Run Tests always add {"type": "wait", "seconds": 5}.

5. Common languages: Java, Python, JavaScript, TypeScript, C++, C#, Go, SQL, Bash.

Add "existing_code" as a top-level field in your JSON response:
{"context": "...", "existing_code": "<exact code from editor>", "actions": [...]}
"""

CODE_ONLY_PROMPT = """\
You are an expert programmer. The screenshot shows a coding challenge.
Read the problem statement, constraints, function signature, and any \
visible examples carefully.
Write a complete, correct solution in the same language shown in the editor.
Return ONLY raw code — no explanations, no markdown fences, no JSON.
The code must be ready to paste directly into the editor as-is.
"""

HAIKU_MODEL  = os.getenv('HAIKU_MODEL',  'claude-haiku-4-5-20251001')
SONNET_MODEL = os.getenv('SONNET_MODEL', 'claude-sonnet-4-6')

# Strong signals: any single match is enough to trigger Sonnet
_CODING_STRONG = (
    'code editor', 'coding challenge', 'coding test', 'ide',
    'code snippet', 'write a solution', 'complete the function',
    'implement the', 'algorithm',
)

# Weak signals: language names / generic words — require 2+ to trigger
_CODING_WEAK = (
    'function', 'programming', 'implement', 'write a',
    'c++', 'java', 'python', 'javascript', 'typescript',
    'go ', 'rust', 'kotlin', 'swift', 'sql', 'bash',
)


def _is_coding(result: dict) -> bool:
    context = result.get('context', '').lower()
    if any(sig in context for sig in _CODING_STRONG):
        return True
    if sum(1 for sig in _CODING_WEAK if sig in context) >= 2:
        return True
    return any(a.get('mode') == 'code' for a in result.get('actions', []))


def _client_instance() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.getenv('ANTHROPIC_API_KEY')
        if not key:
            raise RuntimeError('ANTHROPIC_API_KEY is not set.')
        _client = anthropic.Anthropic(api_key=key)
    return _client


def _img_dims(screen_w: int, screen_h: int) -> tuple[int, int]:
    """Compute the actual image dimensions after the resize step in screen.py."""
    from screen import MAX_LONG_EDGE
    long_edge = max(screen_w, screen_h)
    if long_edge <= MAX_LONG_EDGE:
        return screen_w, screen_h
    scale = MAX_LONG_EDGE / long_edge
    return int(screen_w * scale), int(screen_h * scale)


_MODE_HINTS: dict[str, str] = {
    'click': (
        'MODE: Click-only. Return ONLY "click" and "wait" actions. '
        'Do NOT return "type" or "key" actions. '
        'Identify and click the correct multiple-choice option or button.'
    ),
    'type': (
        'MODE: Type-only. Return ONLY "type", "key", and "wait" actions. '
        'Do NOT return "click" actions. '
        'Type the best answer into the active text field or editor.'
    ),
}


def _messages_payload(b64: str, screen_w: int, screen_h: int,
                      mode: str = 'auto') -> list:
    img_w, img_h = _img_dims(screen_w, screen_h)
    hint = _MODE_HINTS.get(mode, '')
    text = (
        f'Image dimensions: {img_w}x{img_h}. '
        f'Screen resolution: {screen_w}x{screen_h}. '
        'Use the IMAGE dimensions when computing x_pct/y_pct. '
        + (f'{hint} ' if hint else '')
        + 'What do you see and what actions should I take?'
    )
    return [{
        'role': 'user',
        'content': [
            {
                'type': 'image',
                'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b64},
            },
            {'type': 'text', 'text': text},
        ],
    }]


def _call(b64: str, screen_w: int, screen_h: int, model: str,
          mode: str = 'auto') -> dict:
    client = _client_instance()
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=_messages_payload(b64, screen_w, screen_h, mode),
            )
            break
        except anthropic.APIStatusError as exc:
            if exc.status_code == 500 and attempt < 2:
                print(f'[!] API 500 error, retrying ({attempt + 1}/3)...')
                time.sleep(2 ** attempt)
                continue
            raise
    raw = response.content[0].text.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find('{')
        if start != -1:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(raw, start)
            return obj
        raise


def _get_code(b64: str, screen_w: int, screen_h: int) -> str:
    """Ask Sonnet for raw code only — no JSON, no escaping issues."""
    client = _client_instance()
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=SONNET_MODEL,
                max_tokens=8192,
                system=CODE_ONLY_PROMPT,
                messages=_messages_payload(b64, screen_w, screen_h),
            )
            break
        except anthropic.APIStatusError as exc:
            if exc.status_code == 500 and attempt < 2:
                print(f'[!] Sonnet API 500, retrying ({attempt + 1}/3)...')
                time.sleep(2 ** attempt)
                continue
            raise
    raw = response.content[0].text.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    return raw


def analyze(png_bytes: bytes, screen_w: int, screen_h: int,
            mode: str = 'auto') -> dict:
    """
    Haiku handles UI analysis and action sequencing.
    For coding challenges, Sonnet writes the code as plain text (no JSON)
    and it is injected into Haiku's <<CODE>> placeholder.
    mode='click' constrains Claude to click-only actions.
    mode='type'  constrains Claude to type/key-only actions.
    """
    from screen import to_base64
    b64 = to_base64(png_bytes)

    result = _call(b64, screen_w, screen_h, HAIKU_MODEL, mode=mode)

    if _is_coding(result):
        print('[+] Coding challenge detected — fetching code from Sonnet...')
        code = _get_code(b64, screen_w, screen_h)
        print(f'[+] Code ready ({len(code)} chars)')
        for action in result.get('actions', []):
            if action.get('type') == 'type' and action.get('text') == '<<CODE>>':
                action['text'] = code
                break
        else:
            actions = result.get('actions', [])
            for i, action in enumerate(actions):
                if action.get('type') == 'key' and 'ctrl+a' in action.get('key', ''):
                    actions.pop(i)  # remove ctrl+a — not needed with targeted edits
                    actions.insert(i, {'type': 'type', 'text': code, 'mode': 'code'})
                    break
            else:
                actions.append({'type': 'type', 'text': code, 'mode': 'code'})

    return result
