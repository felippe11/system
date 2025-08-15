"""Tests for ensuring static file references in templates exist."""

from __future__ import annotations

import re
from pathlib import Path


TEMPLATE_DIR = Path("templates")
STATIC_DIR = Path("static")


def _extract_paths(content: str) -> set[str]:
    """Return static file paths referenced in the given template content."""
    direct = re.findall(r"(?:src|href)=['\"]?/static/([^'\"]+)", content)
    via_url_for = re.findall(
        r"url_for\(\s*['\"]static['\"]\s*,\s*filename=['\"]([^'\"]+)['\"]", content
    )
    return set(direct) | set(via_url_for)


def test_static_files_exist() -> None:
    """Ensure all static file references in templates resolve to existing files."""
    missing: list[str] = []
    for template in TEMPLATE_DIR.rglob("*.html"):
        content = template.read_text(encoding="utf-8")
        for rel_path in _extract_paths(content):
            if any(marker in rel_path for marker in ("{{", "}}", "${")):
                continue
            if not (STATIC_DIR / rel_path).exists():
                missing.append(f"{template}:{rel_path}")
    assert not missing, f"Missing static files: {missing}"

