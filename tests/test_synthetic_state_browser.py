import os

import pytest
from django.conf import settings
from playwright.sync_api import sync_playwright

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.browser,
    pytest.mark.skipif(
        os.environ.get("RUN_BROWSER_TESTS") != "1",
        reason="Set RUN_BROWSER_TESTS=1 for the installed Edge recovery profile.",
    ),
]


def test_pending_draft_retry_conflict_cleanup_reflow_and_axe(live_server):
    static_root = settings.BASE_DIR / "core" / "static" / "core"
    axe_path = settings.BASE_DIR / "node_modules" / "axe-core" / "axe.min.js"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(bypass_csp=True, viewport={"width": 320, "height": 800})
        context.route(
            "**/static/core/app.css",
            lambda route: route.fulfill(path=static_root / "app.css", content_type="text/css"),
        )
        context.route(
            "**/static/core/app.js",
            lambda route: route.fulfill(
                path=static_root / "app.js", content_type="text/javascript"
            ),
        )
        context.route(
            "**/static/core/synthetic-state.js",
            lambda route: route.fulfill(
                path=static_root / "synthetic-state.js",
                content_type="text/javascript",
            ),
        )
        page = context.new_page()
        page.goto(f"{live_server.url}/_synthetic/state/")

        context.route("**/_synthetic/state/save/", lambda route: route.abort("failed"))
        page.get_by_label("Token B").check()
        page.get_by_text("Stored on this device — not saved online.").wait_for()
        page.reload()
        page.get_by_text("Recovered from this device — not saved online.").wait_for()
        assert page.get_by_label("Token B").is_checked()

        context.unroute("**/_synthetic/state/save/")
        page.get_by_role("button", name="Retry save").click()
        page.get_by_text("Saved online at revision 1.").wait_for()

        other_tab = context.new_page()
        other_tab.goto(f"{live_server.url}/_synthetic/state/")
        page.get_by_label("Token C").check()
        page.get_by_text("Saved online at revision 2.").wait_for()
        other_tab.get_by_label("Token A").check()
        other_tab.get_by_text("Save conflict").wait_for()
        assert other_tab.get_by_text("Another tab saved a newer revision").is_visible()
        other_tab.get_by_role("button", name="Save this device response").click()
        other_tab.get_by_text("Saved online at revision 3.").wait_for()

        context.route("**/_synthetic/state/save/", lambda route: route.abort("failed"))
        other_tab.get_by_label("Token B").check()
        other_tab.get_by_text("Stored on this device — not saved online.").wait_for()
        other_tab.get_by_role("button", name="Clear pending device copy").click()
        other_tab.get_by_text("Pending device copy cleared").wait_for()
        local_draft = other_tab.evaluate(
            """async () => new Promise((resolve, reject) => {
              const key = document.getElementById('synthetic-state-form').dataset.draftKey;
              const request = indexedDB.open('math-platform-synthetic-pending-v1', 1);
              request.onerror = () => reject(request.error);
              request.onsuccess = () => {
                const get = request.result.transaction('drafts').objectStore('drafts')
                  .get(key);
                get.onsuccess = () => resolve(get.result || null);
              };
            })"""
        )
        assert local_draft is None

        assert other_tab.evaluate("document.documentElement.scrollWidth <= innerWidth")
        other_tab.evaluate("document.documentElement.style.fontSize = '200%'")
        assert other_tab.evaluate("document.documentElement.scrollWidth <= innerWidth")
        service_workers = other_tab.evaluate(
            "navigator.serviceWorker.getRegistrations().then(r => r.length)"
        )
        assert service_workers == 0

        other_tab.add_script_tag(path=axe_path)
        results = other_tab.evaluate(
            """async () => axe.run(document, {
              runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']}
            })"""
        )
        assert results["violations"] == []
        browser.close()
