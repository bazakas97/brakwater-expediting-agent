"""Where the data files live.

By default: the data/ folder next to the code. The folder can be changed with the environment
variable AGENT_DATA_DIR (the tests use their own folder, so they never touch the real data).
The code reads these names at the moment it needs them (paths.DECISIONS_PATH), so a test can replace them.
"""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("AGENT_DATA_DIR") or Path(__file__).parent / "data")
DECISIONS_PATH = DATA_DIR / "decisions.json"  # written by build_decisions.py, read by the page
REVIEWS_PATH = DATA_DIR / "reviews.json"      # written by the page (through reviews.py), only this file
