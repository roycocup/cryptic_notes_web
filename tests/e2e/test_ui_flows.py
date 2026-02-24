"""
Playwright UI tests: landing, login, create account, notes (edit/priority/preview), logout, stats.
Run with: pytest tests/e2e/ -v
Or: BASE_URL=http://127.0.0.1:8080 pytest tests/e2e/ -v
"""
import re
import pytest
from playwright.sync_api import expect

CLASS_OPEN = re.compile(r"open")


def test_ui_landing_page_shows_hero_and_create_account(page, base_url):
    """Landing page shows hero title and Create Account button."""
    if not base_url:
        pytest.skip("Server not available: set BASE_URL")
    page.goto("/")
    expect(page.get_by_role("heading", name="Your notes. Truly private.")).to_be_visible()
    expect(page.get_by_role("button", name="Create Account")).to_be_visible()
    expect(page.get_by_role("button", name="Already have an account?")).to_be_visible()


def test_ui_landing_opens_settings_for_mnemonic(page, base_url):
    """Click 'Already have an account?' opens settings drawer with mnemonic form."""
    if not base_url:
        pytest.skip("Server not available: set BASE_URL")
    page.goto("/")
    page.get_by_role("button", name="Already have an account?").click()
    expect(page.locator("#settings-panel")).to_have_class(CLASS_OPEN)
    expect(page.locator("textarea#mnemonic")).to_be_visible()
    expect(page.get_by_role("button", name="Use Mnemonic")).to_be_visible()


def test_ui_login_shows_notes_view(logged_in, base_url):
    """After logging in via settings, notes view and New button are visible."""
    page = logged_in
    expect(page.locator("body")).to_contain_text("Cryptic Notes")
    expect(page.get_by_role("button", name="New")).to_be_visible()
    # Either "Your Notes" or "No notes found"
    assert page.locator("text=Your Notes").is_visible() or page.locator("text=No notes found").is_visible()


def test_ui_create_account_flow(page, base_url):
    """Create Account from landing -> create-account page -> Generate -> redirect to index with session."""
    if not base_url:
        pytest.skip("Server not available: set BASE_URL")
    page.goto("/")
    page.get_by_role("button", name="Create Account").first.click()
    page.wait_for_load_state("networkidle")
    if page.get_by_role("button", name="Generate new mnemonic").is_visible():
        page.get_by_role("button", name="Generate new mnemonic").click()
        page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_contain_text("Cryptic Notes")
    assert page.locator("text=New account created").is_visible() or page.get_by_role("button", name="New").is_visible()


def test_ui_new_note_modal_then_edit_and_save(logged_in, base_url):
    """Create a new note via the New modal; optionally edit it and save."""
    page = logged_in
    page.get_by_role("button", name="New").click()
    expect(page.locator("#new-note-modal")).to_have_class(CLASS_OPEN)
    page.locator("#new-note-title").fill("UI test title")
    page.locator("#new-note-body").fill("UI test body")
    page.locator("#new-note-modal").get_by_role("button", name="Save").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_contain_text("Cryptic Notes")
    expect(page.locator("body")).to_contain_text("UI test title")
    if page.locator("button.edit-btn").count() == 0:
        return
    page.locator("button.edit-btn").first.click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("h1")).to_contain_text("Edit Note")
    page.locator("#title").fill("UI test title updated")
    page.locator("#body").fill("UI test body")
    page.get_by_role("button", name="Save").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_contain_text("UI test title updated")


def test_ui_priority_modal(logged_in, base_url):
    """Open priority modal from a note badge, set value, save; modal closes."""
    page = logged_in
    if page.locator(".priority-badge").count() == 0:
        page.get_by_role("button", name="New").click()
        expect(page.locator("#new-note-modal")).to_have_class(CLASS_OPEN)
        page.locator("#new-note-modal").get_by_role("button", name="Save").click()
        page.wait_for_load_state("networkidle")
    if page.locator(".priority-badge").count() == 0:
        pytest.skip("No notes to set priority on")
    page.locator(".priority-badge").first.click()
    expect(page.locator("#priority-modal")).to_have_class(CLASS_OPEN)
    page.locator("#priority-input").fill("2")
    page.locator("#priority-modal").get_by_role("button", name="Save").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("#priority-modal")).not_to_have_class(CLASS_OPEN)
    expect(page.locator("body")).to_contain_text("Cryptic Notes")


def test_ui_preview_modal(logged_in, base_url):
    """Click Preview on a note; modal opens; close it."""
    page = logged_in
    if page.locator("button:has-text('Preview')").count() == 0:
        page.get_by_role("button", name="New").click()
        expect(page.locator("#new-note-modal")).to_have_class(CLASS_OPEN)
        page.locator("#new-note-modal").get_by_role("button", name="Save").click()
        page.wait_for_load_state("networkidle")
    if page.locator("button:has-text('Preview')").count() == 0:
        pytest.skip("No notes to preview")
    page.get_by_role("button", name="Preview").first.click()
    expect(page.locator("#preview-modal")).to_have_class(CLASS_OPEN)
    expect(page.locator("#preview-modal")).to_contain_text("Close")
    page.locator("#preview-modal button[data-preview-close]").first.click()
    expect(page.locator("#preview-modal")).not_to_have_class(CLASS_OPEN)


def test_ui_logout_returns_to_landing(logged_in, base_url):
    """Open settings, click Log Out; landing page is shown."""
    page = logged_in
    page.get_by_role("button", name="Settings").click()
    expect(page.locator("#settings-panel")).to_have_class(CLASS_OPEN)
    logout_btn = page.locator("#settings-panel").get_by_role("button", name="Log Out")
    logout_btn.dispatch_event("click")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Your notes. Truly private.")).to_be_visible()
    expect(page.get_by_role("button", name="Create Account")).to_be_visible()


def test_ui_stats_page(logged_in, base_url):
    """Open settings, click See stats; stats page shows Total Accounts / Total Notes."""
    page = logged_in
    page.get_by_role("button", name="Settings").click()
    expect(page.locator("#settings-panel")).to_have_class(CLASS_OPEN)
    stats_link = page.locator("#settings-panel").get_by_role("link", name="See stats")
    stats_link.dispatch_event("click")
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_contain_text("Database Statistics")
    expect(page.locator("body")).to_contain_text("Total Accounts")
    expect(page.locator("body")).to_contain_text("Total Notes")
