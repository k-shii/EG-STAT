import subprocess
import sys


def test_can_run_module():
    proc = subprocess.run(
        [sys.executable, "-m", "egstat"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "EG-Stat core loaded" in proc.stdout
