from __future__ import annotations

import math
from egstat.curves import normalized_profile, rpm_fraction
from egstat.models import EngineSpec, RunConfig, Assumptions, Result
from egstat.validate import validate_engine_inputs, has_errors

def rpm_to_rad_s(rpm: float) -> float:
    return (2.0 * math.pi * rpm) / 60.0


def displacement_m3_from_bore_stroke(bore_m: float, stroke_m: float, cylinders: int) -> float:
    if bore_m <= 0 or stroke_m <= 0:
        raise ValueError("bore_m and stroke_m must be > 0")
    if cylinders <= 0:
        raise ValueError("cylinders must be > 0")
    return (math.pi / 4.0) * (bore_m ** 2) * stroke_m * cylinders


def mean_piston_speed_mps(stroke_m: float, rpm: float) -> float:
    if stroke_m <= 0:
        raise ValueError("stroke_m must be > 0")
    if rpm < 0:
        raise ValueError("rpm must be >= 0")
    return 2.0 * stroke_m * (rpm / 60.0)


def torque_nm_from_bmep_pa(bmep_pa: float, displacement_m3: float, revs_per_power: int = 2) -> float:
    """
    For 4-stroke, revs_per_power=2, radians per power cycle = 4*pi.
    For 2-stroke, revs_per_power=1, radians per power cycle = 2*pi.

    Work per power cycle = BMEP * Vd = Torque * radians_per_cycle
    """
    if bmep_pa < 0:
        raise ValueError("bmep_pa must be >= 0")
    if displacement_m3 <= 0:
        raise ValueError("displacement_m3 must be > 0")
    if revs_per_power not in (1, 2):
        raise ValueError("revs_per_power must be 1 (2-stroke) or 2 (4-stroke)")
    radians_per_cycle = 2.0 * math.pi * revs_per_power
    return (bmep_pa * displacement_m3) / radians_per_cycle


def bmep_pa_from_torque_nm(torque_nm: float, displacement_m3: float, revs_per_power: int = 2) -> float:
    if torque_nm < 0:
        raise ValueError("torque_nm must be >= 0")
    if displacement_m3 <= 0:
        raise ValueError("displacement_m3 must be > 0")
    if revs_per_power not in (1, 2):
        raise ValueError("revs_per_power must be 1 (2-stroke) or 2 (4-stroke)")
    radians_per_cycle = 2.0 * math.pi * revs_per_power
    return (torque_nm * radians_per_cycle) / displacement_m3


def power_w_from_torque_rpm(torque_nm: float, rpm: float) -> float:
    if rpm < 0:
        raise ValueError("rpm must be >= 0")
    if torque_nm < 0:
        raise ValueError("torque_nm must be >= 0")
    return torque_nm * rpm_to_rad_s(rpm)


def power_kw_from_torque_rpm(torque_nm: float, rpm: float) -> float:
    return power_w_from_torque_rpm(torque_nm, rpm) / 1000.0


def torque_nm_from_power_w_rpm(power_w: float, rpm: float) -> float:
    if power_w < 0:
        raise ValueError("power_w must be >= 0")
    if rpm <= 0:
        raise ValueError("rpm must be > 0")
    omega = rpm_to_rad_s(rpm)
    return power_w / omega


def rpm_grid(cfg: RunConfig) -> list[int]:
    if cfg.rpm_step <= 0:
        raise ValueError("rpm_step must be > 0")
    if cfg.rpm_max <= cfg.rpm_min:
        raise ValueError("rpm_max must be > rpm_min")
    return list(range(cfg.rpm_min, cfg.rpm_max + 1, cfg.rpm_step))


def _revs_per_power_from_cycle(cycle: str) -> int:
    # Keep simple for now
    return 1 if cycle.strip().lower().startswith("2") else 2


def analyze_basic_curves(
    engine: EngineSpec,
    assumptions: Assumptions,
    cfg: RunConfig,
    *,
    peak_bmep_kpa: float,
    profile: str | None = None,
) -> Result:
    """
    Stage 4: Build BMEP->torque/power curves from templates.
    Inputs are deliberately simple:
      - engine displacement OR bore/stroke/cyl
      - peak BMEP (kPa)
      - a profile (torque_biased / balanced / top_end)
    """

    issues = validate_engine_inputs(
        cylinders=engine.cylinders,
        bore_m=engine.bore_m,
        stroke_m=engine.stroke_m,
        displacement_m3=engine.displacement_m3,
        idle_rpm=engine.idle_rpm,
        redline_rpm=engine.redline_rpm,
    )
    if has_errors(issues):
        return Result(issues=[str(i) for i in issues])

    # Determine displacement
    disp_m3 = engine.displacement_m3
    if disp_m3 is None:
        if engine.bore_m is None or engine.stroke_m is None:
            return Result(issues=[str(i) for i in issues] + ["[ERROR] displacement: Cannot compute displacement (need bore_m+stroke_m or displacement_m3)."])
        disp_m3 = displacement_m3_from_bore_stroke(engine.bore_m, engine.stroke_m, engine.cylinders)

    profile_name = profile if profile is not None else assumptions.ve_profile
    revs_per_power = _revs_per_power_from_cycle(engine.cycle)

    rpms = rpm_grid(cfg)

    peak_bmep_pa = peak_bmep_kpa * 1000.0
    bmep_kpa_curve: list[float] = []
    torque_curve: list[float] = []
    power_kw_curve: list[float] = []

    for rpm in rpms:
        x = rpm_fraction(rpm, engine.idle_rpm, engine.redline_rpm)
        factor = normalized_profile(profile_name, x)
        bmep_pa = peak_bmep_pa * factor
        torque_nm = torque_nm_from_bmep_pa(bmep_pa, disp_m3, revs_per_power=revs_per_power)
        power_kw = power_kw_from_torque_rpm(torque_nm, rpm)

        bmep_kpa_curve.append(bmep_pa / 1000.0)
        torque_curve.append(torque_nm)
        power_kw_curve.append(power_kw)

    # Peaks
    peak_torque_nm = max(torque_curve) if torque_curve else 0.0
    peak_torque_rpm = rpms[torque_curve.index(peak_torque_nm)] if torque_curve else 0

    peak_power_kw = max(power_kw_curve) if power_kw_curve else 0.0
    peak_power_rpm = rpms[power_kw_curve.index(peak_power_kw)] if power_kw_curve else 0

    result = Result(
        scalars={
            "displacement_l": disp_m3 * 1000.0,
            "peak_bmep_kpa": peak_bmep_kpa,
            "peak_torque_nm": peak_torque_nm,
            "peak_torque_rpm": float(peak_torque_rpm),
            "peak_power_kw": peak_power_kw,
            "peak_power_rpm": float(peak_power_rpm),
        },
        curves={
            "rpm": [float(r) for r in rpms],
            "bmep_kpa": bmep_kpa_curve,
            "torque_nm": torque_curve,
            "power_kw": power_kw_curve,
        },
        issues=[str(i) for i in issues if i.level == "WARN"],
    )
    
    # Stage 5 add-ons (fuel, credibility, warnings)
    result = add_stage5_outputs(result, engine, assumptions)
    
    return result

def bsfc_default_g_per_kwh(fuel: str) -> float:
    f = fuel.strip().lower()
    # Rough, defensible defaults for "estimate" mode
    if f == "diesel":
        return 230.0
    if f == "e85":
        return 320.0
    return 270.0  # petrol


def fuel_density_kg_per_l(fuel: str) -> float:
    f = fuel.strip().lower()
    if f == "diesel":
        return 0.832
    if f == "e85":
        return 0.785
    return 0.745  # petrol


def fuel_flow_lph_from_power_kw(power_kw: float, bsfc_g_per_kwh: float, fuel: str) -> float:
    """
    fuel mass flow (g/h) = BSFC (g/kWh) * power (kW)
    volume flow (L/h) = mass(kg/h) / density(kg/L)
    """
    if power_kw < 0:
        raise ValueError("power_kw must be >= 0")
    if bsfc_g_per_kwh <= 0:
        raise ValueError("bsfc_g_per_kwh must be > 0")
    mass_g_per_h = bsfc_g_per_kwh * power_kw
    mass_kg_per_h = mass_g_per_h / 1000.0
    dens = fuel_density_kg_per_l(fuel)
    return mass_kg_per_h / dens


def add_stage5_outputs(
    result: Result,
    engine: EngineSpec,
    assumptions: Assumptions,
) -> Result:
    """
    Mutates/extends Result with fuel estimates + credibility outputs + warnings.
    """
    # Decide BSFC
    bsfc = assumptions.bsfc_g_per_kwh
    if bsfc is None:
        bsfc = bsfc_default_g_per_kwh(assumptions.fuel)

    result.scalars["bsfc_g_per_kwh"] = float(bsfc)

    # WOT fuel at peak power
    peak_power_kw = float(result.scalars.get("peak_power_kw", 0.0))
    wot_lph = fuel_flow_lph_from_power_kw(peak_power_kw, bsfc, assumptions.fuel)
    result.scalars["fuel_wot_lph_at_peak_power"] = float(wot_lph)

    # "Cruise" estimate: assume 20 kW default (can be improved later using vehicle model)
    cruise_kw = 20.0
    cruise_lph = fuel_flow_lph_from_power_kw(cruise_kw, bsfc, assumptions.fuel)
    result.scalars["fuel_cruise_lph_at_20kw"] = float(cruise_lph)

    # Credibility output: piston speed at redline (only if stroke known)
    if engine.stroke_m is not None:
        ps = mean_piston_speed_mps(engine.stroke_m, engine.redline_rpm)
        result.scalars["piston_speed_mps_at_redline"] = float(ps)

        # Warning thresholds (rough but useful)
        if ps > 25.0:
            result.issues.append("[WARN] piston_speed: Very high (>25 m/s). Expect durability risk.")
        elif ps > 20.0:
            result.issues.append("[WARN] piston_speed: High (>20 m/s). Racing-ish territory.")

    # BMEP warning heuristic (depends on profile usage later, keep simple)
    peak_bmep_kpa = float(result.scalars.get("peak_bmep_kpa", 0.0))
    if peak_bmep_kpa > 1600:
        result.issues.append("[WARN] bmep: Very high BMEP (>1600 kPa). Likely boosted / highly tuned.")
    elif peak_bmep_kpa > 1200:
        result.issues.append("[WARN] bmep: High BMEP (>1200 kPa). NA engines may not sustain this.")

    return result
