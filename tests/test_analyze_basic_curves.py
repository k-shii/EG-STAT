from egstat.models import EngineSpec, Assumptions, RunConfig
from egstat.performance import analyze_basic_curves


def test_peak_torque_rpm_moves_with_profile():
    engine = EngineSpec(cylinders=4, displacement_m3=0.001998, idle_rpm=800, redline_rpm=7000)
    cfg = RunConfig(rpm_min=1000, rpm_max=7000, rpm_step=100)

    res_tq = analyze_basic_curves(engine, Assumptions(ve_profile="torque_biased"), cfg, peak_bmep_kpa=1000)
    res_te = analyze_basic_curves(engine, Assumptions(ve_profile="top_end"), cfg, peak_bmep_kpa=1000)

    assert res_tq.scalars["peak_torque_rpm"] < res_te.scalars["peak_torque_rpm"]


def test_peak_torque_matches_bmep_math_at_factor_1():
    # With peak_bmep=1000 kPa and 1.998L 4-stroke:
    # torque = (bmep*Vd)/(4*pi) ≈ 159 Nm
    engine = EngineSpec(cylinders=4, displacement_m3=0.001998, idle_rpm=800, redline_rpm=7000)
    cfg = RunConfig(rpm_min=1000, rpm_max=7000, rpm_step=100)

    res = analyze_basic_curves(engine, Assumptions(ve_profile="balanced"), cfg, peak_bmep_kpa=1000)
    peak_t = res.scalars["peak_torque_nm"]

    assert 150.0 <= peak_t <= 170.0
