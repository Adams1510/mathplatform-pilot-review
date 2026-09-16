import os

import pytest
from django.conf import settings
from playwright.sync_api import sync_playwright

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.browser,
    pytest.mark.skipif(
        os.environ.get("RUN_BROWSER_TESTS") != "1",
        reason="Set RUN_BROWSER_TESTS=1 for the installed Edge accessibility profile.",
    ),
]


def test_topic_entry_keyboard_reflow_and_axe(live_server):
    css_path = settings.BASE_DIR / "core" / "static" / "core" / "app.css"
    js_path = settings.BASE_DIR / "core" / "static" / "core" / "app.js"
    axe_path = settings.BASE_DIR / "node_modules" / "axe-core" / "axe.min.js"
    assert axe_path.exists(), "Run npm ci before the browser gate."

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            bypass_csp=True,
            viewport={"width": 320, "height": 800},
        )
        page = context.new_page()
        page.route(
            "**/static/core/app.css",
            lambda route: route.fulfill(path=css_path, content_type="text/css"),
        )
        page.route(
            "**/static/core/app.js",
            lambda route: route.fulfill(path=js_path, content_type="text/javascript"),
        )
        page.goto(f"{live_server.url}/learn/m1/integers/")

        assert page.locator("h1").inner_text() == "Integers"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.locator(".disclosure-button").focus()
        page.keyboard.press("Enter")
        assert page.locator(".disclosure-button").get_attribute("aria-expanded") == "true"
        assert page.locator("#learning-path").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.evaluate("document.documentElement.style.fontSize = '200%'")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.add_script_tag(path=axe_path)
        results = page.evaluate(
            """async () => axe.run(document, {
              runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']}
            })"""
        )
        assert results["violations"] == []
        browser.close()
