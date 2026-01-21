import os
import subprocess
import sys


def test_can_run_module():
    env = os.environ.copy()
    env["EGSTAT_NONINTERACTIVE_TEST"] = "1"
    proc = subprocess.run(
        [sys.executable, "-m", "egstat"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Interactive mode started" in proc.stdout
