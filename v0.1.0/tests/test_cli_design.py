import subprocess, sys


def test_cli_design_runs():
    proc = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "design",
            "--target-power-kw", "120",
            "--target-power-rpm", "6500",
            "--redline", "7000",
            "--profile", "balanced",
            "--disp-min-cc", "1500",
            "--disp-max-cc", "3000",
            "--disp-step-cc", "250",
            "--cyls", "4", "6",
            "--top-n", "3",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Mode: design" in proc.stdout
    assert "Candidate" in proc.stdout
