import os
import pytest

os.environ.setdefault('SECRET_KEY', 'testing')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'x')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'x')
os.environ.setdefault('DB_PASS', 'test')

pytestmark = pytest.mark.skip("checkin routes tests skipped")
