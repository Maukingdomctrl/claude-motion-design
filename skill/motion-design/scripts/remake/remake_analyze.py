"""Phase 0: extract all frames + audio, detect cuts by mean-abs-diff spikes, build per-cut contact sheets.
Measures the reference's fps and size and writes them to ref/cuts.json (read by the other scripts) and ref/meta.js (read by core.js)."""
import subprocess, json, re
import numpy as np, imageio_ffmpeg
from PIL import Image
from remake_common import H, REF as ref, even, frame_pattern
FF = imageio_ffmpeg.get_ffmpeg_exe()
info = subprocess.run([FF, "-hide_banner", "-i", str(ref)], capture_output=True, text=True).stderr
vs = next(l for l in info.splitlines() if "Video:" in l)
W, Hh = map(int, re.search(r", (\d{2,5})x(\d{2,5})\b", vs).groups())
FPS = float(re.search(r"([\d.]+) fps", vs).group(1))
if not FPS.is_integer() and abs(FPS * 1.001 - round(FPS * 1.001)) < 0.01: FPS = round(FPS * 1.001) / 1.001  # 29.97 -> 30000/1001
FPS = int(FPS) if FPS.is_integer() else FPS
print(f"reference {W}x{Hh} @ {FPS} fps")
full = H / "ref/full"; full.mkdir(parents=True, exist_ok=True)
old = list(full.glob("f*.jpg"))
DIGITS = min(len(p.stem) - 1 for p in old) if old else 5  # keep an existing project's padding (older ones used 4)
if not old:
    subprocess.run([FF, "-v", "error", "-i", str(ref), "-start_number", "0", "-q:v", "3", str(full / frame_pattern("f", "jpg", DIGITS))], check=True)
    subprocess.run([FF, "-v", "error", "-y", "-i", str(ref), "-vn", "-ac", "2", "-ar", "48000", str(H / "ref/audio.wav")], check=True)
frames = sorted(full.glob("f*.jpg"), key=lambda p: int(p.stem[1:]))  # numeric: f10000 must follow f9999
print("frames", len(frames))
small = [np.asarray(Image.open(f).convert("L").resize((192, 108)), dtype=np.float32) for f in frames]
d = np.array([0.0] + [np.abs(small[i] - small[i - 1]).mean() for i in range(1, len(small))])
np.save(H / "ref/diff.npy", d)
# spike = diff much larger than local median
cuts = []
win = max(2, round(FPS / 4))  # local median over +-0.25 s (6 frames at 24 fps)
for i in range(1, len(d)):
    lo, hi = max(1, i - win), min(len(d), i + win + 1)
    loc = np.median(np.concatenate([d[lo:i], d[i + 1:hi]])) if hi - lo > 1 else 0
    if d[i] > 6 and d[i] > 3.5 * (loc + 0.5):
        cuts.append(i)
print("cuts", cuts)
json.dump({"fps": FPS, "n": len(frames), "w": W, "h": Hh, "digits": DIGITS, "cuts": cuts, "diff": [round(float(x), 2) for x in d]}, open(H / "ref/cuts.json", "w"))
(H / "ref/meta.js").write_text(f"window.REMAKE = {json.dumps({'fps': FPS, 'w': W, 'h': Hh, 'n': len(frames)})};\n")
# contact sheet: 4 frames per second with frame numbers
TW, TH = 256, even(256 * Hh / W)
thumbs = []
for i in range(0, len(frames), max(1, round(FPS / 4))):
    im = Image.open(frames[i]).resize((TW, TH))
    thumbs.append((i, im))
cols = 10
from PIL import ImageDraw
(H / "ref/sheet").mkdir(parents=True, exist_ok=True)
for page in range(0, len(thumbs), 80):
    chunk = thumbs[page:page + 80]
    rows = (len(chunk) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * TW, rows * (TH + 16)), "white")
    dr = ImageDraw.Draw(sheet)
    for k, (i, im) in enumerate(chunk):
        x, y = (k % cols) * TW, (k // cols) * (TH + 16)
        sheet.paste(im, (x, y))
        dr.text((x + 4, y + TH + 2), f"f{i}" + (" CUT" if i in cuts else ""), fill="red")
    sheet.save(H / f"ref/sheet/sheet_{page // 80}.jpg", quality=80)
print("sheets done")
