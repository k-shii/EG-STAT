import subprocess
import sys


def test_cli_analyze_with_vehicle_outputs():
    proc = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "analyze",
            "--disp-cc", "1998",
            "--peak-bmep-kpa", "1000",
            "--fuel", "petrol",
            "--profile", "balanced",
            "--mass-kg", "1600",
            "--cd", "0.32",
            "--fa-m2", "2.2",
            "--final-drive", "4.1",
            "--tire-radius-m", "0.31",
            "--gears", "3.6", "2.19", "1.41", "1.12", "0.87", "0.69",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Top speed est" in proc.stdout
    assert "Upshift suggestions" in proc.stdout
