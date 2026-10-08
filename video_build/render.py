"""Grab 1920x1080 frames of web/scene.html via Playwright.

Usage: render.py [--test]  → frames/fNNNNN.jpg (24 fps over 176 s = 4224 frames)
--test renders a dozen keyframes to testframes/ instead.
"""
import asyncio, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
FPS = 24
DUR = 176.0
N = int(DUR * FPS)  # 4224
URL = "file://" + str(ROOT / "web" / "scene.html")
WORKERS = 4

async def main(test=False):
    out = ROOT / ("testframes" if test else "frames")
    out.mkdir(exist_ok=True)
    if test:
        times = [0.5, 3.5, 8, 12.5, 15.5, 20.5, 23.5, 27.5, 33.5, 37.5, 41.5, 45.5,
                 49.5, 51.5, 53, 57.5, 60.5, 65.5, 68.5, 74, 78, 80.5, 85, 91,
                 96.5, 103, 110, 115.5, 123.5, 125.5, 129.5, 134, 138.5, 148, 156,
                 164, 171, 174]
    else:
        times = [i / FPS for i in range(N)]
    t0 = time.time()
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", args=["--force-device-scale-factor=1"])
        pages = []
        for _ in range(WORKERS):
            pg = await b.new_page(viewport={"width": 1920, "height": 1080})
            await pg.goto(URL)
            await pg.wait_for_function("window.__ready === true")
            await pg.evaluate("document.fonts.ready")
            pages.append(pg)
        if test:
            for i, t in enumerate(times):
                await pages[0].evaluate(f"seek({t:.4f})")
                await pages[0].screenshot(path=str(out / f"k{i:02d}_{t:.0f}s.jpg"), type="jpeg", quality=92)
        else:
            chunks = [times[i::WORKERS] for i in range(WORKERS)]
            async def work(pg, ts):
                for t in ts:
                    i = int(round(t * FPS))
                    await pg.evaluate(f"seek({t:.5f})")
                    await pg.screenshot(path=str(out / f"f{i:05d}.jpg"), type="jpeg", quality=92, timeout=30000)
            await asyncio.gather(*[work(pg, ts) for pg, ts in zip(pages, chunks)])
        await b.close()
    print(f"done {len(times)} frames in {time.time()-t0:.0f}s", flush=True)

asyncio.run(main(test="--test" in sys.argv))