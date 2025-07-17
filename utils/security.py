import bleach


def sanitize_input(text: str) -> str:
    """Return a sanitized version of the provided text."""
    if text is None:
        return ""
    return bleach.clean(text, tags=[], strip=True)


def password_is_strong(password: str, min_length: int = 8) -> bool:
    """Simple password strength validation."""
    if not password or len(password) < min_length:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit

