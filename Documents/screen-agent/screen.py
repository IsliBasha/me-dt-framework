"""Screenshot capture — returns compressed JPEG bytes and original screen dimensions."""

import io
import base64
import mss
from PIL import Image

MAX_LONG_EDGE = 1280
JPEG_QUALITY  = 82


def capture() -> tuple[bytes, int, int]:
    """
    Capture primary monitor, resize to MAX_LONG_EDGE on longest side,
    encode as JPEG. Returns (jpeg_bytes, original_width, original_height).
    Original dimensions are kept for accurate click coordinate math.
    """
    with mss.MSS() as sct:
        mon = sct.monitors[1]
        raw = sct.grab(mon)
        orig_w, orig_h = raw.width, raw.height
        img = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')

    long_edge = max(img.size)
    if long_edge > MAX_LONG_EDGE:
        scale = MAX_LONG_EDGE / long_edge
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue(), orig_w, orig_h


def to_base64(img_bytes: bytes) -> str:
    return base64.standard_b64encode(img_bytes).decode()
