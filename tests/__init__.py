"""SMARTBUS test-suite. Fast password hashing is used for tests only."""
import os
import sys

os.environ.setdefault("SMARTBUS_PBKDF2_ITERATIONS", "1000")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
