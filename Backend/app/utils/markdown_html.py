"""Convert Markdown source text into HTML for rich display.

Uploaded `.md` files are stored as `text_html` so the TipTap editor renders them
with their original formatting (headings, lists, emphasis, code) instead of showing
raw markdown syntax. The canonical plain `text` used for RAG is derived separately
via `html_to_text`.
"""
import markdown


def markdown_to_html(text: str | None) -> str:
    """Render Markdown to HTML. Returns an empty string for empty input."""
    if not text or not text.strip():
        return ""
    # `extra` enables fenced code, tables, etc.; `sane_lists` keeps list nesting sane.
    return markdown.markdown(text, extensions=["extra", "sane_lists"])
