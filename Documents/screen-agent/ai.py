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
    {"type": "type",   "text": "<exact text to type>", "mode": "text"},
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
"""

HAIKU_MODEL  = os.getenv('HAIKU_MODEL',  'claude-haiku-4-5-20251001')
SONNET_MODEL = os.getenv('SONNET_MODEL', 'claude-sonnet-4-6')


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


def analyze(png_bytes: bytes, screen_w: int, screen_h: int,
            mode: str = 'auto') -> dict:
    """
    Analyze a screenshot and return a structured action plan.
    mode='click' → Haiku, constrained to click/wait actions only.
    mode='type'  → Sonnet, constrained to type/key/wait actions only.
    mode='auto'  → Haiku, all action types allowed.
    """
    from screen import to_base64
    b64 = to_base64(png_bytes)
    model = SONNET_MODEL if mode == 'type' else HAIKU_MODEL
    return _call(b64, screen_w, screen_h, model, mode=mode)
