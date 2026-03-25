"""
Shared pytest configuration for the KalaOS test suite.

Sets environment variables that must be in place before any backend module
is imported (e.g. rate-limit overrides, DB path).
"""

import os
import tempfile

# Use a temporary file-based SQLite DB for tests (not :memory: — each
# sqlite3.connect(":memory:") opens a different database).
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ.setdefault("KALA_DB_PATH", _tmp_db.name)

# Raise rate limits high enough that the test suite (which may issue dozens
# of login/forgot-password calls in a single process) never hits them.
os.environ.setdefault("KALA_RATE_LIMIT_LOGIN",  "10000/minute")
os.environ.setdefault("KALA_RATE_LIMIT_FORGOT", "10000/minute")
