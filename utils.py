import re
import markdown
from config import NOTES_SIZE_LIMIT


def truncate_words(text: str, limit: int = NOTES_SIZE_LIMIT) -> str:
    word_matches = list(re.finditer(r"\S+", text))
    if len(word_matches) <= limit:
        return text
    end_index = word_matches[limit - 1].end()
    return text[:end_index] + "..."


def render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html5",
    )


def note_sort_key(note: dict) -> tuple:
    priority = note.get("priority")
    priority_group = 0 if priority is not None else 1
    priority_value = priority if priority is not None else 0
    timestamp = note.get("updated_at") or note.get("created_at")
    if timestamp is None:
        timestamp_sort = float("inf")
    else:
        timestamp_sort = -timestamp.timestamp()
    return (priority_group, priority_value, timestamp_sort)
