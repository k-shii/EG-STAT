import subprocess
import sys


def test_cli_match_runs():
    proc = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "match",
            "--disp-cc", "1998",
            "--redline", "7000",
            "--profile", "balanced",
            "--target-power-kw", "120",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Mode: match" in proc.stdout
    assert "Confidence:" in proc.stdout
    assert "Peak BMEP:" in proc.stdout
