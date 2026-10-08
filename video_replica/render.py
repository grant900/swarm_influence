"""Render video.html frame by frame with system Chrome.

  uv run python render.py stills 3 12 24 ...      # PNG stills into stills/
  uv run python render.py video --workers 6       # silent 30fps segments -> silent.mp4
"""
import argparse
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
URL = (ROOT / "video.html").as_uri()
FPS = 30


def open_page(p):
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto(URL)
    pg.wait_for_function("window.READY === true", timeout=60000)
    return b, pg


def stills(times):
    out = ROOT / "stills"
    out.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b, pg = open_page(p)
        for t in times:
            pg.evaluate(f"render({t})")
            pg.screenshot(path=str(out / f"t{float(t):06.1f}.png"))
        b.close()


def segment(args):
    idx, f0, f1 = args
    path = ROOT / "segments" / f"seg{idx:02d}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg",
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                           "-r", str(FPS), str(path)], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b, pg = open_page(p)
        for f in range(f0, f1):
            pg.evaluate(f"render({f / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=94))
        b.close()
    ff.stdin.close()
    ff.wait()
    return path


def video(workers):
    (ROOT / "segments").mkdir(exist_ok=True)
    with sync_playwright() as p:
        b, pg = open_page(p)
        dur = pg.evaluate("window.DURATION")
        b.close()
    total = int(round(dur * FPS))
    step = -(-total // workers)
    jobs = [(i, i * step, min(total, (i + 1) * step)) for i in range(workers)]
    with ProcessPoolExecutor(workers) as ex:
        paths = list(ex.map(segment, jobs))
    lst = ROOT / "segments" / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in paths))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(ROOT / "silent.mp4")], check=True)
    print("frames", total, "->", ROOT / "silent.mp4")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["stills", "video"])
    ap.add_argument("times", nargs="*", type=float)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    stills(a.times) if a.mode == "stills" else video(a.workers)
