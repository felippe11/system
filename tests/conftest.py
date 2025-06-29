import importlib
import pathlib
import sys

# Ensure repository root is on sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import sitecustomize to preload real utils before tests possibly monkeypatch it
try:
    import sitecustomize  # noqa: F401
except Exception:  # pragma: no cover - optional
    pass
