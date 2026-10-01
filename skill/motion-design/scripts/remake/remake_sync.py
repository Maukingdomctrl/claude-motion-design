"""sync.py — build the deliverables from full-render frames in out/full/o_fNNNNN.png.
  sync.py encode   -> out/remake_silent.mp4 (reference fps from ref/cuts.json, h264 BT.709) and out/remake.mp4 (muxed with out/mix.wav if present)
  sync.py split    -> out/split_screen.mp4 : REF left | OURS right, labelled "original" / "opus 5.5 copy", white bg (the X post format)
  sync.py stacked  -> out/sync_check.mp4 : REF top / OURS bottom, frame-locked, for QA
"""
import subprocess, sys
import imageio_ffmpeg
from remake_common import H, REF, meta, font, even, frame_pattern
FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = H / "out"; FULL = OUT / "full"
M = meta()
ENC = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "slow", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart"]
mode = sys.argv[1]
if mode == "encode":
    subprocess.run([FF, "-v", "error", "-y", "-framerate", str(M["fps"]), "-i", str(FULL / frame_pattern("o_f", "png")), *ENC, str(OUT / "remake_silent.mp4")], check=True)
    mix = OUT / "mix.wav"
    if mix.exists():
        subprocess.run([FF, "-v", "error", "-y", "-i", str(OUT / "remake_silent.mp4"), "-i", str(mix), "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(OUT / "remake.mp4")], check=True)
    print("encoded")
elif mode == "split":
    # Labels are drawn with Pillow and overlaid: the imageio-ffmpeg build has no drawtext filter.
    # 1920x1080 post: two panels fitted into 880-wide columns at x=60 and x=980, centred vertically, labels 46 px above.
    from PIL import Image, ImageDraw
    pw, ph = 880, even(880 * M["h"] / M["w"])
    if ph > 948: pw, ph = even(948 * M["w"] / M["h"]), 948  # tall references: leave room for the labels
    y = (1080 - ph) // 2; xl, xr = 60 + (880 - pw) // 2, 980 + (880 - pw) // 2
    fnt = font(22)
    labels = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(labels)
    for txt, x in [("original", xl), ("opus 5.5 copy", xr)]:
        d.rectangle([x, y - 46, x + len(txt) * 13 + 24 - 1, y - 46 + 34 - 1], fill="black")
        d.text((x + 12, y - 39), txt, font=fnt, fill="white")
    lab_png = OUT / "split_labels.png"; labels.save(lab_png)
    vf = (f"[0:v]scale={pw}:{ph},setsar=1,pad=1920:1080:{xl}:{y}:0xF3F4F6[bg];[1:v]scale={pw}:{ph},setsar=1[b];"
          f"[bg][b]overlay={xr}:{y}:shortest=1[s];[s][2:v]overlay=0:0,setsar=1[v]")
    src = OUT / ("remake.mp4" if (OUT / "remake.mp4").exists() else "remake_silent.mp4")
    audio = ["-map", "1:a?"] if (OUT / "remake.mp4").exists() else []
    subprocess.run([FF, "-v", "error", "-y", "-i", str(REF), "-i", str(src), "-i", str(lab_png), "-filter_complex", vf, "-map", "[v]", *audio, *ENC, "-c:a", "aac", "-b:a", "256k", str(OUT / "split_screen.mp4")], check=True)
    print("split ->", OUT / "split_screen.mp4")
elif mode == "stacked":
    src = OUT / "remake_silent.mp4"
    subprocess.run([FF, "-v", "error", "-y", "-i", str(REF), "-i", str(src), "-filter_complex", "[0:v]scale=960:-2,setsar=1[a];[1:v]scale=960:-2,setsar=1[b];[a][b]vstack=inputs=2:shortest=1[v]", "-map", "[v]", *ENC, str(OUT / "sync_check.mp4")], check=True)
    print("stacked ->", OUT / "sync_check.mp4")
