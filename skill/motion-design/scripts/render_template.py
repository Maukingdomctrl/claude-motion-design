"""Render film.html frame by frame.
probe t1 t2 ... -> probe/sheet.png | beats -> one frame per beat, beats/beats.png | full -> N subframes/frame blended with tmix -> out/video.mp4 | pops [video] -> single-frame pop scan.
Serve the folder first: python -m http.server 8000. Options (defaults = the Howseen LinkedIn 4:5 film):
  --size 1080x1350  --fps 60  --duration 24  --subframes 8  --crf 14  --url http://localhost:8000/film.html (or FILM_URL)
  --bpm 120 --beat-offset 0.45 (beats)  --work-dir sub (full; use one per version so parallel renders don't clash)
e.g. python render.py full --size 1920x1080 --duration 15 --work-dir sub_v2"""
import argparse, asyncio, math, os, shutil, subprocess
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from playwright.async_api import async_playwright

HERE = Path(__file__).parent
FF = imageio_ffmpeg.get_ffmpeg_exe()


def size(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("cmd", choices=["probe", "beats", "full", "pops"])
ap.add_argument("args", nargs="*", help="probe: times in seconds; pops: optional video path (default out/video.mp4)")
ap.add_argument("--size", type=size, default=(1080, 1350), help="viewport = video size, WxH (16:9 1920x1080, 4:5 1080x1350, 1:1 1440x1440)")
ap.add_argument("--fps", type=int, default=60)
ap.add_argument("--duration", type=float, default=24.0, help="film length in seconds")
ap.add_argument("--subframes", type=int, default=8, help="motion-blur subframes per frame (6-8 for fast moves, 4 ghosts)")
ap.add_argument("--crf", type=int, default=14)
ap.add_argument("--url", default=os.environ.get("FILM_URL", "http://localhost:8000/film.html"))
ap.add_argument("--bpm", type=float, default=120.0)
ap.add_argument("--beat-offset", type=float, default=0.45, help="time of the first beat frame in seconds")
ap.add_argument("--work-dir", default="sub", help="subframe folder for full, relative to this script")
A = ap.parse_args()
W, H = A.size
FPS, T, SUB = A.fps, A.duration, A.subframes


async def open_page(p):
    b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg = await b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type in ("error", "warning") else None)
    await pg.goto(A.url)
    await pg.wait_for_function("window.ready === true", timeout=120000)
    return b, pg, errs


async def shot(pg, t, path, fmt="png"):
    await pg.evaluate(f"window.seek({t})")
    el = await pg.query_selector("#stage")
    await el.screenshot(path=str(path), type=fmt, **({"quality": 95} if fmt == "jpeg" else {}))


def sheet(folder, pattern, n, out, cols=4, size=360):
    rows = -(-n // cols)
    subprocess.run([FF, "-v", "error", "-y", "-i", str(folder / pattern), "-vf",
                    f"scale={size}:-1,tile={cols}x{rows}:padding=6:color=white", "-frames:v", "1", str(out)], check=True)


async def probe(times, folder="probe", name="sheet.png", cols=4):
    out = HERE / folder; shutil.rmtree(out, ignore_errors=True); out.mkdir()
    async with async_playwright() as p:
        b, pg, errs = await open_page(p)
        for i, t in enumerate(times): await shot(pg, t, out / f"p_{i:03d}.png")
        await b.close()
    if errs: print("PAGE ERRORS:", errs[:8])
    sheet(out, "p_%03d.png", len(times), out / name, cols=cols)
    print(f"{folder}:", len(times), "->", out / name)


def beat_times():
    beat = 60 / A.bpm
    return [A.beat_offset + i * beat for i in range(math.ceil((T - A.beat_offset) / beat))]


async def full():
    sub = HERE / A.work_dir; shutil.rmtree(sub, ignore_errors=True); sub.mkdir()
    n, k = int(round(T * FPS)), 0
    offs = [(j - (SUB - 1) / 2) / (FPS * SUB) for j in range(SUB)]
    async with async_playwright() as p:
        b, pg, errs = await open_page(p)
        for i in range(n):
            for o in offs:
                t = min(T - 1e-3, max(0.0, i / FPS + o))
                await shot(pg, t, sub / f"s_{k:06d}.jpg", "jpeg"); k += 1
            if i % FPS == 0: print(f"frame {i}/{n}", flush=True)
        await b.close()
    if errs: print("PAGE ERRORS:", errs[:8])
    (HERE / "out").mkdir(exist_ok=True)
    subprocess.run([FF, "-v", "error", "-y", "-framerate", str(FPS * SUB), "-i", str(sub / "s_%06d.jpg"),
                    "-vf", f"tmix=frames={SUB},select='eq(mod(n\\,{SUB})\\,{SUB - 1})',setpts=N/{FPS}/TB", "-r", str(FPS),
                    "-c:v", "libx264", "-crf", str(A.crf), "-preset", "slow", "-pix_fmt", "yuv420p", str(HERE / "out/video.mp4")], check=True)
    print("video ->", HERE / "out/video.mp4")


def pops(path=None):
    path = path or HERE / "out/video.mp4"
    raw = subprocess.run([FF, "-v", "quiet", "-i", str(path), "-vf", "scale=180:180,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 180, 180).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    hits = []
    for i in range(1, len(d) - 1):
        nb = max(d[i - 1], d[i + 1], 0.3)
        if d[i] > 3 * nb and d[i] > 2.0: hits.append((i + 1, round((i + 1) / FPS, 3), round(float(d[i]), 2), round(float(nb), 2)))
    print("pops:", len(hits))
    for h in hits: print("  frame", h[0], "t", h[1], "diff", h[2], "neighbours", h[3])


if __name__ == "__main__":
    if A.cmd == "probe": asyncio.run(probe([float(x) for x in A.args]))
    elif A.cmd == "beats": asyncio.run(probe(beat_times(), "beats", "beats.png", cols=9))
    elif A.cmd == "full": asyncio.run(full())
    elif A.cmd == "pops": pops(A.args[0] if A.args else None)
