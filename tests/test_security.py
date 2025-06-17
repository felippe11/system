import importlib.util
import pathlib

file_path = pathlib.Path(__file__).resolve().parents[1] / 'utils' / 'security.py'
spec = importlib.util.spec_from_file_location('security', file_path)
security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security)
sanitize_input = security.sanitize_input


def test_sanitize_input_removes_tags():
    assert sanitize_input('<b>Hello</b>') == 'Hello'
    assert sanitize_input('<script>alert(1)</script>Hi') == 'alert(1)Hi'
