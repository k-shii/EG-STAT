import math

from egstat.performance import (
    displacement_m3_from_bore_stroke,
    mean_piston_speed_mps,
    torque_nm_from_bmep_pa,
    bmep_pa_from_torque_nm,
    power_w_from_torque_rpm,
)


def test_displacement_86x86_i4_is_about_2l():
    disp = displacement_m3_from_bore_stroke(0.086, 0.086, 4)
    liters = disp * 1000.0
    assert abs(liters - 1.9982288568717088) < 1e-9


def test_mean_piston_speed():
    mps = mean_piston_speed_mps(0.086, 7000)
    assert abs(mps - 20.066666666666666) < 1e-12


def test_bmep_torque_roundtrip_4stroke():
    disp = displacement_m3_from_bore_stroke(0.086, 0.086, 4)
    bmep = 1_000_000.0  # Pa (1000 kPa)
    t = torque_nm_from_bmep_pa(bmep, disp, revs_per_power=2)
    bmep2 = bmep_pa_from_torque_nm(t, disp, revs_per_power=2)
    assert abs(bmep2 - bmep) < 1e-6


def test_power_from_torque_rpm():
    t = 200.0
    rpm = 6000.0
    p = power_w_from_torque_rpm(t, rpm)
    expected = t * (2.0 * math.pi * rpm / 60.0)
    assert abs(p - expected) < 1e-9
