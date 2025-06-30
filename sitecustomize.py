import importlib
try:
    import utils  # Preload real utils package before tests may stub it
except Exception:
    pass
