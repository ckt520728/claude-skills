"""
Drive the dashboard in a real browser. API tests cannot see browser form validation, which once blocked
every submission.

    uv run --no-project --python 3.12 --with-requirements requirements.txt --with playwright python tests/browser_smoke.py --fake
    uv run ... python tests/browser_smoke.py [URL]          # read-only checks against a running server (default http://127.0.0.1:8090/)

--fake starts tests/fake_server.py (canned data, port 8091) and also runs the checks that start runs or change the KB.
Against a real server those checks are skipped, because they would spend money or write to the knowledge base.
--screenshot PATH saves a full-page screenshot. Set BROWSER_CHANNEL to override the browser (default msedge, then bundled chromium).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
failures = []


def check(label, ok):
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        failures.append(label)


def skip(label):
    print(f"SKIP  {label} (needs --fake)")


def launch(p):
    channel = os.environ.get("BROWSER_CHANNEL", "msedge")
    try:
        return p.chromium.launch(channel=channel, headless=True)
    except Exception as err:  # Edge missing: fall back to bundled chromium
        print(f"note: channel {channel} failed ({str(err).splitlines()[0]}); trying bundled chromium")
        return p.chromium.launch(headless=True)


def run(url, fake, shot):
    with sync_playwright() as p:
        browser = launch(p)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors, posts = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        def capture(route):
            req = route.request
            if req.method == "POST":
                posts.append(req.post_data)
            route.continue_()

        page.route("**/api/research", capture)
        page.goto(url)
        page.wait_for_function("document.getElementById('run').disabled === false", timeout=15000)
        check("page loads and the Start button is enabled", page.is_enabled("#run"))
        page.wait_for_function("document.querySelectorAll('#providers .chip').length > 0", timeout=10000)
        chips = page.locator("#providers .chip")
        check("provider chips render from /api/config", chips.count() > 0)
        if fake:
            check("an available and an unavailable chip are both shown", page.locator("#providers .chip.ok").count() == 1 and page.locator("#providers .chip.bad").count() == 1)
        for sel in ("planner", "executor", "auditor"):
            check(f"{sel} select is filled from tiers", page.locator(f"#{sel} option").count() > 0)
        page.fill("#topic", "A valid test topic")
        check("the form is valid with its default values", page.evaluate("document.getElementById('form').checkValidity()"))
        for value in ("1", "8", "2.5"):
            page.fill("#budget", value)
            check(f"budget {value} is accepted by the browser", page.evaluate("document.getElementById('budget').checkValidity()"))
        page.fill("#budget", "2.5")

        # Knowledge base (read-only)
        kb_pages = page.evaluate("fetch('/api/kb/pages').then(r => r.json()).then(d => (d.pages || d).length)")
        if kb_pages or fake:
            page.wait_for_function("document.querySelectorAll('#kbResults button').length > 0", timeout=10000)
            check("KB page list renders", page.locator("#kbResults button").count() > 0)
            page.fill("#kbQuery", "recursive")
            page.wait_for_function("document.querySelectorAll('#kbResults button').length >= 1", timeout=10000)
            time.sleep(0.6)
            buttons = page.locator("#kbResults button")
            check("KB search lists matching pages", buttons.count() >= 1 or not fake)
        else:
            time.sleep(1.0)
            check("empty KB shows an empty state, not fake pages", page.locator("#kbResults button").count() == 0)
        if fake:
            check("KB search filters (query 'recursive' gives 2 of 3 pages)", buttons.count() == 2)
        if kb_pages or fake:
            page.locator("#kbResults button").first.click()
            page.wait_for_selector("#kbTitle", timeout=10000)
            check("clicking a page renders it", page.inner_text("#kbTitle").strip() != "")
        if fake:
            page.fill("#kbQuery", "")
            page.wait_for_function("document.querySelectorAll('#kbResults button').length === 3", timeout=10000)
            page.locator("#kbResults button", has_text="RSI overview").click()
            page.wait_for_function("document.getElementById('kbTitle') && document.getElementById('kbTitle').textContent === 'RSI overview'", timeout=10000)
            check("HTML in page text is escaped, not executed", page.locator("#kbPage script").count() == 0 and "<script>" in page.inner_text("#kbPage"))
            check("frontmatter is rendered", page.locator("#kbPage dl.fm dt").count() >= 3)
            page.locator("#kbPage a.wiki", has_text="recursive-self-improvement").click()
            page.wait_for_function("document.getElementById('kbTitle').textContent === 'Recursive self-improvement'", timeout=10000)
            check("a wiki-link inside a page navigates to that page", True)
        box = page.locator("#kbMap").bounding_box()
        size = page.evaluate("[document.getElementById('kbMap').width, document.getElementById('kbMap').height]")
        check(f"concept map canvas has non-zero size {size}", bool(box) and box["width"] > 0 and box["height"] > 0 and size[0] > 0 and size[1] > 0)
        painted = page.evaluate("""() => { const c = document.getElementById('kbMap'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; for (let i = 3; i < d.length; i += 4) if (d[i]) return true; return false; }""")
        check("concept map canvas has drawn pixels" if fake else "concept map canvas readable", painted or not fake)
        check("gaps list renders", page.locator("#gaps li").count() >= 1 or not kb_pages)
        check("KB fitness shows a score", "%" in page.inner_text("#fitness") or "No fitness" in page.inner_text("#fitness"))
        if fake:
            check("fitness tiles render", page.locator("#fitness .tile").count() >= 5)
            check("past run is auto-selected: graph SVG shows canned nodes", page.locator("svg.graph g.node").count() == 4)
            check("source status table shows LIVE/FALLBACK/UNAVAILABLE", all(s in page.inner_text("#sources") for s in ("Live", "Fallback", "Unavailable")))
            check("audits list shows verdicts and findings", "REVISE" in page.inner_text("#audits") and "Claim 3 lacks a citation" in page.inner_text("#audits"))
            check("deliverables show verified and needs-review badges", "verified" in page.inner_text("#deliverables") and "needs review" in page.inner_text("#deliverables"))
            check("deliverable links point at /outputs/runs/", page.locator("#deliverables a.file").first.get_attribute("href").startswith("outputs/runs/"))
            check("per-run KB block shows fitness before to after", "→" in page.inner_text("#runKb"))
            check("Robin panel ranks 3 hypotheses with BTL and win rate", page.locator("#robinBox tbody tr").count() >= 3 and "Fixture hypothesis two" in page.inner_text("#robinBox"))
            check("Robin panel shows status, rate and Finch as N/A (never PASS)", all(x in page.inner_text("#robinBox") for x in ("Proposal only", "0.0%", "N/A")))
            # Robin settings: a setting that would change nothing is disabled
            check("consensus is disabled while trajectories = 1", page.is_disabled("#consensus"))
            page.select_option("#trajectories", "3")
            check("consensus is enabled when trajectories > 1", page.is_enabled("#consensus"))
            page.uncheck("#robin")
            check("turning Robin off disables its settings", page.is_disabled("#candidates") and page.is_disabled("#trajectories") and page.is_disabled("#consensus"))
            page.check("#robin")
            page.select_option("#consensus", "0.75")

        if fake:
            # Start: POST body and live graph
            page.select_option("#loops", "3")
            page.click("#run")
            page.wait_for_function("document.getElementById('cancel').hidden === false", timeout=10000)
            check("Start sent exactly one POST", len(posts) == 1)
            body = json.loads(posts[0]) if posts else {}
            check(f"POST body has topic/loops/budget_usd/planner/executor/auditor {sorted(body)}", {"topic", "loops", "budget_usd", "planner", "executor", "auditor"} <= set(body))
            check("POST values are typed correctly", body.get("loops") == 3 and body.get("budget_usd") == 2.5 and body.get("topic") == "A valid test topic" and body.get("planner") == "claude-opus-fixture" and body.get("executor") == "claude-sonnet-fixture")
            check("POST carries typed Robin settings", body.get("robin") is True and body.get("candidates") == 6 and body.get("trajectories") == 3 and body.get("consensus") == 0.75)
            page.wait_for_function("document.querySelector('svg.graph g.node.running') !== null", timeout=10000)
            check("live graph shows a running node", page.locator("svg.graph g.node.running").count() == 1)
            check("graph nodes show tier and attempts", "high" in page.inner_text("#graphBox") and "attempts" in page.inner_text("#graphBox"))
            # Cancel
            page.click("#cancel")
            page.wait_for_function("document.getElementById('run').disabled === false && document.getElementById('cancel').hidden === true", timeout=15000)
            check("Cancel ends the run and re-enables Start", page.is_enabled("#run"))
            check("progress shows Cancelled", "Cancelled" in page.inner_text("#progress"))
            check("history lists the new run and the old run", page.locator("#runs .run").count() == 2)
            # Improve
            before = page.locator("#ledger tr td:not(.note)").count()
            page.click("#improve")
            page.wait_for_function("document.querySelectorAll('#ledger tr').length > 0 && document.getElementById('improve').disabled === false && document.getElementById('improveMsg').textContent.length > 0", timeout=10000)
            check("improve posts and the ledger gains a row", before == 0 and page.locator("#ledger tr").count() == 1 and "PROMOTE" in page.inner_text("#ledger"))
            check("ledger shows chain_ok", "verified" in page.inner_text("#chain"))
            check("fitness refreshed after improve", "87.0%" in page.inner_text("#fitness"))

        # Phone layout
        phone = browser.new_page(viewport={"width": 390, "height": 800})
        phone.goto(url)
        phone.wait_for_function("document.getElementById('run').disabled === false", timeout=15000)
        if kb_pages or fake:
            phone.wait_for_function("document.querySelectorAll('#kbResults button').length > 0", timeout=10000)
        else:
            phone.wait_for_timeout(1000)
        check("no sideways scrolling on a phone", phone.evaluate("document.documentElement.scrollWidth") <= 390)

        if shot:
            page.set_viewport_size({"width": 1280, "height": 900})
            page.wait_for_timeout(800)
            page.screenshot(path=shot, full_page=True)
            print(f"screenshot: {shot}")

        check(f"no browser errors {errors}", not errors)
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", default=os.environ.get("DASHBOARD_URL", "http://127.0.0.1:8090/"))
    ap.add_argument("--fake", action="store_true", help="start tests/fake_server.py on 8091 and run all checks")
    ap.add_argument("--screenshot", default="")
    args = ap.parse_args()
    server = None
    url = args.url
    if args.fake:
        url = "http://127.0.0.1:8091/"
        server = subprocess.Popen([sys.executable, str(HERE / "fake_server.py")], stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urlopen(url + "api/health", timeout=1).read()
                break
            except Exception:
                time.sleep(0.2)
    try:
        run(url, args.fake, args.screenshot)
    finally:
        if server:
            server.terminate()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
