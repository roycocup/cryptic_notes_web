"""
E2E fixtures: base_url (from env or by starting the app), Playwright context, and optional login.
"""
import os
import sys
import time
import random
import subprocess
import pytest

SAMPLE_MNEMONIC = "word1 word2 word3 word4 word5 word6"


def _website_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the app: from BASE_URL env, or start uvicorn and return its URL."""
    url = os.environ.get("BASE_URL", "").rstrip("/")
    if url:
        return url
    port = random.randint(10000, 65535)
    cwd = _website_dir()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=cwd,
        env=os.environ,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        for _ in range(100):
            try:
                import urllib.request
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as r:
                    if r.status in (200, 303, 307):
                        break
            except Exception:
                time.sleep(0.1)
        else:
            proc.terminate()
            proc.wait(timeout=2)
            yield None
            return
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url):
    """Inject base_url into Playwright context so page.goto('/') works."""
    if base_url:
        return {**browser_context_args, "base_url": base_url}
    return browser_context_args


@pytest.fixture
def logged_in(page, base_url):
    """Navigate to app and log in with SAMPLE_MNEMONIC if landing is shown; return page."""
    if not base_url:
        pytest.skip("Server not available: set BASE_URL or run from website dir with credentials")
    page.goto("/")
    # If landing page, open settings drawer then submit mnemonic form
    if page.get_by_role("button", name="Already have an account?").is_visible():
        page.get_by_role("button", name="Already have an account?").click()
        page.locator("textarea#mnemonic").wait_for(state="visible", timeout=5000)
        page.locator("textarea#mnemonic").fill(SAMPLE_MNEMONIC)
        page.get_by_role("button", name="Use Mnemonic").click()
        page.wait_for_load_state("networkidle")
    return page
