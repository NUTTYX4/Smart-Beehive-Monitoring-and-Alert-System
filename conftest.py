# conftest.py — project root
# Ensures all test scripts can import project modules regardless of how they are invoked.
import sys
from pathlib import Path

# Add the project root (where config.py, sensors/, utils/ etc. live) to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
