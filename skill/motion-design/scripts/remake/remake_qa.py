"""QA sheets: ref|ours once per second (33 per page) + group seams (last 2 / first 2 frames of each group, from shots/groups.json)
+ old-brand colour scan. Frame count and fps come from ref/cuts.json."""
import numpy as np
from PIL import Image, ImageDraw
from remake_common import H, meta, groups, even, frame
M = meta(); N, FPS = M["n"], M["fps"]
TW, TH = 480, even(480 * M["h"] / M["w"])
Q = H / "out/qa"; Q.mkdir(parents=True, exist_ok=True)
def pair(F):
    r = Image.open(H / "ref/full" / frame("f", F, "jpg")).convert("RGB").resize((TW, TH))
    o = Image.open(H / "out/full" / frame("o_f", F, "png")).convert("RGB").resize((TW, TH))
    c = Image.new("RGB", (2 * TW + 10, TH + 20), "white"); c.paste(r, (0, 20)); c.paste(o, (TW + 10, 20))
    ImageDraw.Draw(c).text((4, 4), f"F{F}", fill="red"); return c
def sheet(frames, name, cols=3):
    tiles = [pair(F) for F in frames]; rows = -(-len(tiles) // cols); w, h = tiles[0].size
    s = Image.new("RGB", (cols * w, rows * h), "white")
    for i, t in enumerate(tiles): s.paste(t, ((i % cols) * w, (i // cols) * h))
    s.save(Q / name, quality=78)
secs = [round(s * FPS) for s in range(int(N / FPS) + 1) if round(s * FPS) < N]
for p in range(0, len(secs), 33): sheet(secs[p:p + 33], f"persec_{p // 33 + 1}.jpg")
seams = [F for _, (a, b) in sorted(groups().items())[1:] for F in range(a - 2, a + 2)]
if seams: sheet(seams, "seams.jpg", cols=2)
else: print("no shots/groups.json: run remake_stub.py to get seams.jpg")
# old-brand colour scan: reddish/orange saturated pixels in ours (edit the mask for your reference's brand colour)
bad = []
for F in range(0, N, 4):
    a = np.asarray(Image.open(H / "out/full" / frame("o_f", F, "png")).convert("RGB").resize((TW, TH)), dtype=np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (r > 180) & (r - g > 60) & (r - b > 60) & (g > 60)
    if m.sum() > 150 * TW * TH / (480 * 270): bad.append((F, int(m.sum())))
print("old-brand-colour frames:", bad[:40], "count", len(bad))
