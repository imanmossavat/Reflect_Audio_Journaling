"""Convert rich HTML (from the TipTap editor) into clean plain text.

The plain-text result is what feeds chunking / embeddings / tags / chat context,
so it must never contain markup. Uses only the stdlib HTML parser — no extra deps.
"""
from html.parser import HTMLParser

# Tags whose boundaries should become line breaks in the plain text.
_BLOCK_TAGS = {
    "p", "div", "br", "tr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "pre",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")
        if tag == "li":
            self._parts.append("\n- ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def html_to_text(html: str | None) -> str:
    """Strip HTML tags and collapse whitespace into readable plain text."""
    if not html:
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    raw = parser.get_text()

    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        # Keep content lines; allow a single blank line between blocks.
        if stripped or (lines and lines[-1] != ""):
            lines.append(stripped)
    return "\n".join(lines).strip()
