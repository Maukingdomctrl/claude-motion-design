"""Shared settings for the remake scripts. remake_analyze.py measures the reference video and writes ref/cuts.json
(fps, frame count, size, frame-number digits, cuts); remake_stub.py writes shots/groups.json. Everything else reads them from here."""
import json
from functools import lru_cache
from pathlib import Path

H = Path(__file__).parent
REF = H / "ref/reference.mp4"


def meta():
    """{'fps', 'n', 'w', 'h', 'digits', 'cuts'} of the reference; defaults (24 fps, 1920x1080) until remake_analyze.py has run.
    digits = zero-padding of frame file names: 5 for new projects, 4 for ones analysed before it was recorded."""
    m = {"fps": 24, "n": 0, "w": 1920, "h": 1080, "digits": 4, "cuts": []}
    p = H / "ref/cuts.json"
    if p.exists(): m.update(json.loads(p.read_text()))
    return m


def groups():
    """{'G1': [f0, f1], ...} from shots/groups.json (written by remake_stub.py), or {} if it doesn't exist yet."""
    p = H / "shots/groups.json"
    return json.loads(p.read_text()) if p.exists() else {}


@lru_cache(None)
def _digits():
    return meta()["digits"]


def frame(prefix, F, ext, digits=None):
    """Frame file name, e.g. frame('o_f', 12, 'png') -> 'o_f00012.png' (padding from meta() unless given)."""
    return f"{prefix}{F:0{digits or _digits()}d}.{ext}"


def frame_pattern(prefix, ext, digits=None):
    """ffmpeg image-sequence pattern matching frame(), e.g. 'o_f%05d.png'."""
    return f"{prefix}%0{digits or _digits()}d.{ext}"


def font(size):
    from PIL import ImageFont
    for f in ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        try: return ImageFont.truetype(f, size)
        except OSError: pass
    return ImageFont.load_default(size)


def even(x):
    return int(x / 2 + 0.5) * 2
