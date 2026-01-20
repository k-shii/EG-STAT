import subprocess
import sys


def test_cli_works_with_presets_only():
    proc = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "analyze",
            "--disp-cc", "1998",
            "--peak-bmep-kpa", "1000",
            "--engine-preset", "na_street",
            "--vehicle-preset", "sedan",
            "--gearbox-preset", "6mt_typical",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Top speed est" in proc.stdout
    assert "Upshift suggestions" in proc.stdout
