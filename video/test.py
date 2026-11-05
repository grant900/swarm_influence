import pathlib
import sys
from playwright.sync_api import sync_playwright
ts=[float(x) for x in sys.argv[1:]]
with sync_playwright() as p:
    br=p.chromium.launch(channel="chrome"); pg=br.new_page(viewport={"width":1920,"height":1080})
    pg.goto(pathlib.Path(__file__).with_name("scene.html").resolve().as_uri()); pg.evaluate("document.fonts.ready.then(()=>1)"); pg.wait_for_timeout(500)
    for t in ts:
        pg.evaluate(f"setT({t})"); pg.screenshot(path=str(pathlib.Path(__file__).with_name(f"t_{t}.png")))
    br.close()
