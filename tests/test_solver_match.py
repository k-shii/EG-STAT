from math import pi

from egstat.models import EngineSpec, Assumptions
from egstat.solver import match_engine


def test_match_infers_bore_stroke_from_disp():
    eng = EngineSpec(
        cylinders=4,
        cycle="4-stroke",
        bore_m=None,
        stroke_m=None,
        displacement_m3=0.001998,  # 1.998 L
        idle_rpm=800,
        redline_rpm=7000,
    )
    a = Assumptions(ve_profile="balanced", fuel="petrol", bsfc_g_per_kwh=None)

    m = match_engine(eng, a, target_power_kw=100.0)

    assert m.engine.bore_m is not None
    assert m.engine.stroke_m is not None
    assert m.engine.displacement_m3 is not None
    assert m.confidence < 1.0
    assert any("bore/stroke ratio" in s for s in m.assumptions_made)


def test_match_infers_bmep_from_target_power():
    disp_m3 = 0.002
    redline = 7000
    power_kw = 120.0
    rpm = int(round(0.88 * redline))

    eng = EngineSpec(
        cylinders=4,
        cycle="4-stroke",
        bore_m=None,
        stroke_m=None,
        displacement_m3=disp_m3,
        idle_rpm=800,
        redline_rpm=redline,
    )
    a = Assumptions(ve_profile="balanced", fuel="petrol", bsfc_g_per_kwh=None)

    m = match_engine(eng, a, target_power_kw=power_kw, target_power_rpm=rpm)

    # expected bmep: torque = P/omega, bmep = torque*(4*pi)/Vd
    omega = 2.0 * pi * (rpm / 60.0)
    torque = (power_kw * 1000.0) / omega
    expected_kpa = (torque * (4.0 * pi) / disp_m3) / 1000.0

    assert abs(m.peak_bmep_kpa - expected_kpa) / expected_kpa < 0.02
