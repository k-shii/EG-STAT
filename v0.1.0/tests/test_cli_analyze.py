import subprocess
import sys


def test_cli_analyze_runs():
    proc = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "analyze",
            "--disp-cc", "1998",
            "--peak-bmep-kpa", "1000",
            "--idle", "800",
            "--redline", "7000",
            "--profile", "balanced",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Peak torque" in proc.stdout
    assert "Peak power" in proc.stdout
