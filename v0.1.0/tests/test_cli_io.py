import subprocess
import sys


def test_cli_save_and_load_json(tmp_path):
    jpath = tmp_path / "run.json"

    p1 = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "analyze",
            "--disp-cc", "1998",
            "--peak-bmep-kpa", "1000",
            "--engine-preset", "na_street",
            "--vehicle-preset", "sedan",
            "--gearbox-preset", "6mt_typical",
            "--save-json", str(jpath),
        ],
        capture_output=True,
        text=True,
    )
    assert p1.returncode == 0
    assert jpath.exists()

    p2 = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "analyze",
            "--load-json", str(jpath),
        ],
        capture_output=True,
        text=True,
    )
    assert p2.returncode == 0
    assert "Displacement" in p2.stdout


def test_cli_export_csv(tmp_path):
    jpath = tmp_path / "run.json"
    cpath = tmp_path / "out.csv"

    p1 = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "analyze",
            "--disp-cc", "1998",
            "--peak-bmep-kpa", "1000",
            "--engine-preset", "na_street",
            "--vehicle-preset", "sedan",
            "--gearbox-preset", "6mt_typical",
            "--save-json", str(jpath),
        ],
        capture_output=True,
        text=True,
    )
    assert p1.returncode == 0

    p2 = subprocess.run(
        [
            sys.executable, "-m", "egstat.cli", "analyze",
            "--load-json", str(jpath),
            "--export-csv", str(cpath),
        ],
        capture_output=True,
        text=True,
    )
    assert p2.returncode == 0
    assert cpath.exists()
