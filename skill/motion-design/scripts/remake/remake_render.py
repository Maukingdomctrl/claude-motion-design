"""render.py — Playwright renderer for the frame-locked remake.
usage:
  render.py stills  OUT F1 F2 ...      -> OUT/o_FNNNN.png
  render.py compare OUT F1 F2 ...      -> OUT/c_FNNNN.jpg (ref | ours, labelled) + OUT/compare_sheet.jpg
  render.py full    OUT F0 F1          -> OUT/fNNNN.png for F0 <= F < F1
Use a separate OUT dir per agent (e.g. out/G2) so parallel runs never collide. Max ~15 frames per call for stills/compare.
FPS and stage size come from ref/cuts.json (remake_analyze.py). Set REMAKE_URL to your served index.html.
"""
import asyncio, sys, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import imageio_ffmpeg
from playwright.async_api import async_playwright
from remake_common import H, meta, font, even

FF = imageio_ffmpeg.get_ffmpeg_exe()
import os
URL = os.environ.get("REMAKE_URL", "http://localhost:8768/remake/index.html")  # set REMAKE_URL to your served index.html
M = meta(); FPS, W, HT = M["fps"], M["w"], M["h"]
TW, TH = 960, even(960 * HT / W)  # compare tile size


async def run(frames, out: Path, fmt="png"):
    out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--disable-gpu-vsync", "--font-render-hinting=none"])
        pg = await b.new_page(viewport={"width": W, "height": HT}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
        await pg.goto(URL)
        await pg.wait_for_function("window.ready === true", timeout=120000)
        el = await pg.query_selector("#stage")
        paths = []
        for F in frames:
            await pg.evaluate(f"window.seek({F / FPS + 1e-6})")
            await pg.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            pth = out / f"o_f{F:04d}.png"
            await el.screenshot(path=str(pth))
            paths.append(pth)
        await b.close()
    if errs: print("PAGE ERRORS:", errs[:10])
    return paths


def compare(frames, out: Path):
    paths = asyncio.run(run(frames, out))
    fnt = font(34)
    tiles = []
    for F, p in zip(frames, paths):
        ref = Image.open(H / f"ref/full/f{F:04d}.jpg").convert("RGB").resize((TW, TH))
        ours = Image.open(p).convert("RGB").resize((TW, TH))
        c = Image.new("RGB", (2 * TW + 10, TH + 50), "white"); c.paste(ref, (0, 50)); c.paste(ours, (TW + 10, 50))
        d = ImageDraw.Draw(c); d.text((10, 8), f"REF f{F}", fill="red", font=fnt); d.text((TW + 20, 8), f"OURS f{F}", fill="blue", font=fnt)
        cp = out / f"c_f{F:04d}.jpg"; c.save(cp, quality=85); tiles.append(c)
    cols = 2; rows = -(-len(tiles) // cols)
    sw, sh = tiles[0].width // 2, tiles[0].height // 2
    sheet = Image.new("RGB", (cols * sw, rows * sh), "white")
    for i, t in enumerate(tiles): sheet.paste(t.resize((sw, sh)), ((i % cols) * sw, (i // cols) * sh))
    sheet.save(out / "compare_sheet.jpg", quality=80)
    print("compare ->", out / "compare_sheet.jpg")


if __name__ == "__main__":
    mode, out = sys.argv[1], H / sys.argv[2]
    nums = [int(x) for x in sys.argv[3:]]
    if mode == "stills":
        asyncio.run(run(nums, out)); print("stills ->", out)
    elif mode == "compare":
        compare(nums, out)
    elif mode == "full":
        asyncio.run(run(list(range(nums[0], nums[1])), out)); print("full", nums, "->", out)
