import builtins
import sys

import egstat.ui as ui


def _mock_input(monkeypatch, inputs):
    it = iter(inputs)
    monkeypatch.setattr(builtins, "input", lambda _: next(it))


def test_is_interactive_true(monkeypatch):
    class FakeStdin:
        def isatty(self):
            return True

    monkeypatch.setattr(sys, "stdin", FakeStdin())
    assert ui.is_interactive() is True


def test_is_interactive_false(monkeypatch):
    class FakeStdin:
        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", FakeStdin())
    assert ui.is_interactive() is False


def test_prompt_yes_no_defaults(monkeypatch):
    _mock_input(monkeypatch, [""])
    assert ui.prompt_yes_no("Confirm", default=True) is True
    _mock_input(monkeypatch, [""])
    assert ui.prompt_yes_no("Confirm", default=False) is False


def test_prompt_yes_no_explicit(monkeypatch):
    _mock_input(monkeypatch, ["n"])
    assert ui.prompt_yes_no("Confirm", default=True) is False
    _mock_input(monkeypatch, ["y"])
    assert ui.prompt_yes_no("Confirm", default=False) is True


def test_prompt_int_with_retry(monkeypatch):
    _mock_input(monkeypatch, ["bad", "5"])
    assert ui.prompt_int("Value", default=None, min_value=1) == 5


def test_prompt_float_allow_auto(monkeypatch):
    _mock_input(monkeypatch, ["auto"])
    assert ui.prompt_float("Value", allow_empty=True) is None


def test_prompt_choice(monkeypatch):
    _mock_input(monkeypatch, ["2"])
    assert ui.prompt_choice("Pick", ["alpha", "bravo"], default="alpha") == "bravo"
    _mock_input(monkeypatch, ["ALPHA"])
    assert ui.prompt_choice("Pick", ["alpha", "bravo"], default="bravo") == "alpha"


def test_prompt_menu(monkeypatch):
    _mock_input(monkeypatch, [""])
    assert ui.prompt_menu(["A", "B", "C"], default_index=2) == 2
    _mock_input(monkeypatch, ["q"])
    assert ui.prompt_menu(["A", "B", "C"], default_index=1) == 3


def test_prompt_preset(monkeypatch):
    presets = [("na", "NA"), ("turbo", "Turbo")]
    _mock_input(monkeypatch, ["0"])
    assert ui.prompt_preset("Preset", presets, allow_none=True) is None
    _mock_input(monkeypatch, ["2"])
    assert ui.prompt_preset("Preset", presets, allow_none=True) == "turbo"


def test_prompt_float_list(monkeypatch):
    _mock_input(monkeypatch, ["1, 2 3"])
    assert ui.prompt_float_list("Ratios") == [1.0, 2.0, 3.0]
    _mock_input(monkeypatch, [""])
    assert ui.prompt_float_list("Ratios", default=[1.5, 2.5]) == [1.5, 2.5]


def test_render_ascii_table(capsys):
    curves = {
        "rpm": [1000, 1500, 2000],
        "torque_nm": [100, 120, 140],
        "power_kw": [20, 30, 40],
        "bmep_kpa": [800, 900, 1000],
    }
    ui.render_ascii_table(curves, step_rpm=500)
    out = capsys.readouterr().out
    assert "Sampled every ~500 rpm" in out
    assert "rpm" in out
    assert "torque_nm" in out
    assert "power_kw" in out
    assert "bmep_kpa" in out


def test_render_ascii_curves_width(capsys):
    curves = {
        "rpm": [1000, 1500, 2000],
        "torque_nm": [0, 50, 100],
        "power_kw": [10, 20, 30],
    }
    ui.render_ascii_curves(curves, step_rpm=500)
    out = capsys.readouterr().out.splitlines()
    bar_lines = [
        line
        for line in out
        if "|" in line and (
            line.strip().startswith("1000")
            or line.strip().startswith("1500")
            or line.strip().startswith("2000")
        )
    ]
    assert bar_lines
    for line in bar_lines:
        left = line.split("|", 1)[1]
        bar = left.split("|", 1)[0]
        assert len(bar) == ui.BAR_WIDTH
