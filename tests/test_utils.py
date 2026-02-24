import pytest
from datetime import datetime
from utils import truncate_words, render_markdown, note_sort_key


class TestTruncateWords:
    def test_truncate_words_under_limit(self):
        text = "one two three"
        result = truncate_words(text, limit=10)
        assert result == text

    def test_truncate_words_at_limit(self):
        text = "one two three four five"
        result = truncate_words(text, limit=5)
        assert result == text

    def test_truncate_words_over_limit(self):
        text = "one two three four five six seven eight"
        result = truncate_words(text, limit=5)
        assert result == "one two three four five..."

    def test_truncate_words_with_extra_spaces(self):
        text = "one  two   three    four"
        result = truncate_words(text, limit=3)
        assert result == "one  two   three..."

    def test_truncate_words_empty_string(self):
        result = truncate_words("", limit=5)
        assert result == ""

    def test_truncate_words_single_word(self):
        result = truncate_words("word", limit=1)
        assert result == "word"

    def test_truncate_words_custom_limit(self):
        text = "one two three four five"
        result = truncate_words(text, limit=2)
        assert result == "one two..."


class TestRenderMarkdown:
    def test_render_markdown_basic(self):
        text = "This is **bold** text"
        result = render_markdown(text)
        assert "<strong>bold</strong>" in result or "<b>bold</b>" in result

    def test_render_markdown_plain_text(self):
        text = "Plain text without markdown"
        result = render_markdown(text)
        assert "Plain text without markdown" in result

    def test_render_markdown_headers(self):
        text = "# Header 1\n## Header 2"
        result = render_markdown(text)
        assert "<h1>" in result or "Header 1" in result

    def test_render_markdown_lists(self):
        text = "- Item 1\n- Item 2"
        result = render_markdown(text)
        assert "Item 1" in result

    def test_render_markdown_empty_string(self):
        result = render_markdown("")
        assert result == ""

    def test_render_markdown_newlines(self):
        text = "Line 1\nLine 2"
        result = render_markdown(text)
        assert "Line 1" in result and "Line 2" in result


class TestNoteSortKey:
    def test_sort_key_with_priority(self):
        note = {
            "priority": 5,
            "updated_at": datetime(2024, 1, 2),
        }
        key = note_sort_key(note)
        assert key[0] == 0  # priority_group
        assert key[1] == 5  # priority_value
        assert key[2] < 0  # negative timestamp

    def test_sort_key_without_priority(self):
        note = {
            "priority": None,
            "updated_at": datetime(2024, 1, 2),
        }
        key = note_sort_key(note)
        assert key[0] == 1  # priority_group
        assert key[1] == 0  # priority_value
        assert key[2] < 0  # negative timestamp

    def test_sort_key_no_timestamp(self):
        note = {
            "priority": 3,
        }
        key = note_sort_key(note)
        assert key[0] == 0
        assert key[1] == 3
        assert key[2] == float("inf")

    def test_sort_key_uses_created_at_when_no_updated_at(self):
        note = {
            "priority": 2,
            "created_at": datetime(2024, 1, 1),
        }
        key = note_sort_key(note)
        assert key[0] == 0
        assert key[1] == 2
        assert key[2] < 0

    def test_sort_key_prioritizes_updated_at_over_created_at(self):
        note = {
            "priority": 1,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 2),
        }
        key = note_sort_key(note)
        # Should use updated_at timestamp
        updated_key = note_sort_key({"priority": 1, "updated_at": datetime(2024, 1, 2)})
        assert key[2] == updated_key[2]

    def test_sort_key_priority_zero(self):
        note = {
            "priority": 0,
            "updated_at": datetime(2024, 1, 2),
        }
        key = note_sort_key(note)
        assert key[0] == 0
        assert key[1] == 0
