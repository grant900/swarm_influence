import sys, os
from playwright.sync_api import sync_playwright
out, fps, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
here=os.path.dirname(os.path.abspath(__file__))
os.makedirs(out, exist_ok=True)
with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome", args=["--force-device-scale-factor=1"])
    pg = br.new_page(viewport={"width":1920,"height":1080})
    pg.goto("file://"+here+"/scene.html"); pg.evaluate("document.fonts.ready.then(()=>1)"); pg.wait_for_timeout(500)
    for i in range(a,b):
        pg.evaluate(f"setT({i/fps})")
        pg.screenshot(path=f"{out}/f{i:05d}.jpg", type="jpeg", quality=92)
    br.close()
