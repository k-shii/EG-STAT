import os
import subprocess
import sys


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "egstat.cli", *args]
    kwargs = {"capture_output": True, "text": True}
    if env is not None:
        kwargs["env"] = env
    return subprocess.run(cmd, **kwargs)


def test_cli_help_routes_to_legacy():
    proc = run_cli("--help")
    assert proc.returncode == 0
    assert "analyze" in proc.stdout


def test_cli_version_flag_exits():
    proc = run_cli("--version")
    assert proc.returncode == 0
    assert "EG-Stat" in proc.stdout


def test_cli_analyze_help():
    proc = run_cli("analyze", "--help")
    assert proc.returncode == 0
    assert "analyze" in proc.stdout


def test_cli_match_help():
    proc = run_cli("match", "--help")
    assert proc.returncode == 0
    assert "match" in proc.stdout


def test_cli_design_help():
    proc = run_cli("design", "--help")
    assert proc.returncode == 0
    assert "design" in proc.stdout


def test_cli_no_args_starts_interactive_marker():
    env = os.environ.copy()
    env["EGSTAT_NONINTERACTIVE_TEST"] = "1"
    proc = run_cli(env=env)
    assert proc.returncode == 0
    assert "Interactive mode started" in proc.stdout


def test_cli_ui_flag_starts_interactive_marker():
    env = os.environ.copy()
    env["EGSTAT_NONINTERACTIVE_TEST"] = "1"
    proc = run_cli("-ui", env=env)
    assert proc.returncode == 0
    assert "Interactive mode started" in proc.stdout
