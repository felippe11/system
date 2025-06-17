import bleach


def sanitize_input(text: str) -> str:
    """Return a sanitized version of the provided text."""
    if text is None:
        return ""
    return bleach.clean(text, tags=[], strip=True)

