"""Kept for old instructions: the dashboard checks now live in scripts/verify_dashboard.py."""
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.argv = [str(Path(__file__).resolve().parent / "scripts" / "verify_dashboard.py")]
    runpy.run_path(sys.argv[0], run_name="__main__")
