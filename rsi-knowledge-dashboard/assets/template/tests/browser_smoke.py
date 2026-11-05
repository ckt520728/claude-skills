"""
Drive the running dashboard in a real browser, spending nothing. API tests cannot see browser form
validation, which once blocked every submission. Start the server first, then run:

    uv run --no-project --python 3.12 --with playwright python tests/browser_smoke.py

Set BROWSER_CHANNEL to chrome if Edge is not installed.
"""

import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("DASHBOARD_URL", "http://127.0.0.1:8080/")
failures = []


def check(label, ok):
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        failures.append(label)


with sync_playwright() as p:
    browser = p.chromium.launch(channel=os.environ.get("BROWSER_CHANNEL", "msedge"), headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(URL)
    page.wait_for_function("document.getElementById('run').disabled === false", timeout=15000)
    check("page loads and the button is enabled", page.is_enabled("#run"))
    check("the models list is filled in", page.locator("#model option").count() > 0)
    page.fill("#topic", "A valid test topic")
    check("the form is valid with its default values", page.evaluate("document.getElementById('form').checkValidity()"))
    for value in ("1", "8", "2.5"):
        page.fill("#budget", value)
        check(f"budget {value} is accepted by the browser", page.evaluate("document.getElementById('budget').checkValidity()"))

    # The server refuses this, so nothing runs and nothing is spent. Skip browser validation to reach it.
    page.evaluate("document.getElementById('form').noValidate = true")
    page.fill("#topic", "x")
    page.click("#run")
    page.wait_for_function("document.getElementById('message').textContent.length > 0", timeout=10000)
    check("a refused request shows its message", "3 to 300" in page.inner_text("#message"))
    check("the button is usable again after a refusal", page.is_enabled("#run"))

    phone = browser.new_page(viewport={"width": 390, "height": 800})
    phone.goto(URL)
    phone.wait_for_function("document.getElementById('run').disabled === false", timeout=15000)
    check("no sideways scrolling on a phone", phone.evaluate("document.documentElement.scrollWidth") <= 390)

    # The refused request above logs an expected 400 to the console.
    unexpected = [e for e in errors if "400" not in e]
    check(f"no browser errors {unexpected}", not unexpected)
    browser.close()

sys.exit(1 if failures else 0)
