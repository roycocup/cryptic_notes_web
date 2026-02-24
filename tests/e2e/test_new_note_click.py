"""
E2E tests for the New note flow: New opens a modal for title/content; nothing to do with mnemonic in the UI.
User must be logged in (have a session) to create notes. Mnemonic is only for login, not for creating notes.
Run with: pytest tests/e2e/ -v
Or with existing server: BASE_URL=http://127.0.0.1:8080 pytest tests/e2e/ -v
"""
import re
import pytest
from playwright.sync_api import expect

CLASS_OPEN = re.compile(r"open")


def test_new_note_button_not_visible_when_not_logged_in(page, base_url):
    """When not logged in, the New button is not visible (user must login first)."""
    if not base_url:
        pytest.skip("Server not available: set BASE_URL")
    page.goto("/")
    expect(page.get_by_role("button", name="New")).not_to_be_visible()
    expect(page.get_by_role("heading", name="Your notes. Truly private.")).to_be_visible()


def test_new_note_requires_session(page, base_url):
    """POST to /new without a session (no cookie, no form mnemonic) returns error page."""
    if not base_url:
        pytest.skip("Server not available: set BASE_URL")
    page.goto("/")
    response = page.request.post(f"{base_url}/new", data={})
    assert response.status == 200
    body_text = response.text()
    assert "error" in body_text.lower() or "missing" in body_text.lower() or "mnemonic" in body_text.lower()


def test_new_note_opens_modal(logged_in, base_url):
    """Clicking New opens the new-note modal with title and content fields (no mnemonic in UI)."""
    page = logged_in
    new_btn = page.get_by_role("button", name="New")
    expect(new_btn).to_be_visible()
    new_btn.click()
    expect(page.locator("#new-note-modal")).to_have_class(CLASS_OPEN)
    expect(page.locator("#new-note-modal")).to_contain_text("New note")
    expect(page.locator("#new-note-title")).to_be_visible()
    expect(page.locator("#new-note-body")).to_be_visible()
    expect(page.locator("#new-note-modal").locator('input[name="mnemonic"][type="hidden"]')).to_have_count(1)
    expect(page.get_by_role("button", name="Save")).to_be_visible()
    expect(page.get_by_role("button", name="Cancel")).to_be_visible()


def test_new_note_modal_submit_creates_note(logged_in, base_url):
    """Submit the new-note modal with title and content; note is created and list updates."""
    page = logged_in
    page.get_by_role("button", name="New").click()
    expect(page.locator("#new-note-modal")).to_have_class(CLASS_OPEN)
    page.locator("#new-note-title").fill("Modal note title")
    page.locator("#new-note-body").fill("Modal note content")
    with page.expect_navigation(wait_until="load", timeout=10000):
        page.locator("#new-note-modal").get_by_role("button", name="Save").click()
    expect(page.locator("body")).to_contain_text("Cryptic Notes")
    expect(page.locator("body")).to_contain_text("Modal note title")
    expect(page.locator("body")).to_contain_text("Modal note content")


def test_click_new_note_submits_and_succeeds(logged_in, base_url):
    """Open new-note modal, submit (empty or filled); expect no 404 and notes view."""
    page = logged_in
    post_new_status = []

    def on_response(response):
        url = response.url.rstrip("/")
        if url.endswith("/new") and response.request.method == "POST":
            post_new_status.append(response.status)

    page.on("response", on_response)
    page.get_by_role("button", name="New").click()
    expect(page.locator("#new-note-modal")).to_have_class(CLASS_OPEN)
    with page.expect_navigation(wait_until="load", timeout=10000):
        page.locator("#new-note-modal").get_by_role("button", name="Save").click()

    assert post_new_status, "POST to /new should have been sent"
    assert 404 not in post_new_status, "POST to /new must not return 404 (got %s)" % post_new_status
    expect(page.locator("body")).to_contain_text("Cryptic Notes")
    expect(page.get_by_role("button", name="New")).to_be_visible()
