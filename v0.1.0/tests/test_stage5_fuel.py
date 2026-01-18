from egstat.models import EngineSpec, Assumptions, RunConfig
from egstat.performance import analyze_basic_curves


def test_stage5_adds_fuel_outputs():
    engine = EngineSpec(cylinders=4, displacement_m3=0.001998, idle_rpm=800, redline_rpm=7000)
    cfg = RunConfig(rpm_min=1000, rpm_max=7000, rpm_step=100)
    res = analyze_basic_curves(engine, Assumptions(ve_profile="balanced", fuel="petrol"), cfg, peak_bmep_kpa=1000)

    assert "bsfc_g_per_kwh" in res.scalars
    assert "fuel_wot_lph_at_peak_power" in res.scalars
    assert "fuel_cruise_lph_at_20kw" in res.scalars

    assert res.scalars["fuel_wot_lph_at_peak_power"] > 0


def test_diesel_uses_lower_bsfc_than_petrol_default():
    engine = EngineSpec(cylinders=4, displacement_m3=0.001998, idle_rpm=800, redline_rpm=7000)
    cfg = RunConfig(rpm_min=1000, rpm_max=7000, rpm_step=100)

    petrol = analyze_basic_curves(engine, Assumptions(ve_profile="balanced", fuel="petrol"), cfg, peak_bmep_kpa=1000)
    diesel = analyze_basic_curves(engine, Assumptions(ve_profile="balanced", fuel="diesel"), cfg, peak_bmep_kpa=1000)

    assert diesel.scalars["bsfc_g_per_kwh"] < petrol.scalars["bsfc_g_per_kwh"]
