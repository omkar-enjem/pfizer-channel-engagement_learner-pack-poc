"""The check set: 18 records with hand-agreed answers must all match (see checks/)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_check_set_matches():
    r = subprocess.run([sys.executable, "checks/run_checks.py"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-500:]
    assert "18 of 18" in r.stdout
