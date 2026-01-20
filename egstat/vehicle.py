from __future__ import annotations

import math

from egstat.models import VehicleSpec, DrivetrainSpec, EngineSpec, Result

G = 9.80665

DEFAULT_RHO = 1.225
DEFAULT_CRR = 0.012
DEFAULT_DRIVETRAIN_EFF = 0.90


def speed_mps_from_rpm(rpm: float, gear_ratio: float, final_drive: float, tire_radius_m: float) -> float:
    if rpm < 0:
        raise ValueError("rpm must be >= 0")
    if gear_ratio <= 0 or final_drive <= 0 or tire_radius_m <= 0:
        raise ValueError("gear_ratio, final_drive, tire_radius_m must be > 0")

    wheel_rpm = rpm / (gear_ratio * final_drive)
    circumference_m = 2.0 * math.pi * tire_radius_m
    return (wheel_rpm * circumference_m) / 60.0


def speed_kph_from_rpm(rpm: float, gear_ratio: float, final_drive: float, tire_radius_m: float) -> float:
    return speed_mps_from_rpm(rpm, gear_ratio, final_drive, tire_radius_m) * 3.6


def road_load_power_w(
    v_mps: float,
    *,
    mass_kg: float,
    cd: float,
    frontal_area_m2: float,
    crr: float = DEFAULT_CRR,
    air_density_kg_m3: float = DEFAULT_RHO,
) -> float:
    if v_mps < 0:
        raise ValueError("v_mps must be >= 0")
    if mass_kg <= 0 or cd <= 0 or frontal_area_m2 <= 0:
        raise ValueError("mass_kg, cd, frontal_area_m2 must be > 0")
    if crr <= 0 or air_density_kg_m3 <= 0:
        raise ValueError("crr, air_density_kg_m3 must be > 0")

    cda = cd * frontal_area_m2
    p_aero = 0.5 * air_density_kg_m3 * cda * (v_mps ** 3)
    f_rr = crr * mass_kg * G
    p_rr = f_rr * v_mps
    return p_aero + p_rr


def per_gear_redline_speeds_kph(engine: EngineSpec, drivetrain: DrivetrainSpec) -> list[float]:
    if drivetrain.gears is None or drivetrain.final_drive is None or drivetrain.tire_radius_m is None:
        raise ValueError("drivetrain.gears, final_drive, tire_radius_m required")
    out: list[float] = []
    for gr in drivetrain.gears:
        out.append(speed_kph_from_rpm(engine.redline_rpm, gr, drivetrain.final_drive, drivetrain.tire_radius_m))
    return out


def estimate_top_speed(
    result: Result,
    engine: EngineSpec,
    vehicle: VehicleSpec,
    drivetrain: DrivetrainSpec,
) -> dict[str, float]:
    if drivetrain.gears is None or drivetrain.final_drive is None or drivetrain.tire_radius_m is None:
        raise ValueError("drivetrain.gears, final_drive, tire_radius_m required")

    if vehicle.mass_kg is None or vehicle.cd is None or vehicle.frontal_area_m2 is None:
        raise ValueError("vehicle.mass_kg, cd, frontal_area_m2 required")

    if "rpm" not in result.curves or "power_kw" not in result.curves:
        raise ValueError("Result must contain curves: rpm, power_kw")

    rpms = [float(x) for x in result.curves["rpm"]]
    power_kw = [float(x) for x in result.curves["power_kw"]]

    rpm_cap = min(engine.redline_rpm, max(rpms) if rpms else engine.redline_rpm)
    eff = drivetrain.drivetrain_efficiency if drivetrain.drivetrain_efficiency is not None else DEFAULT_DRIVETRAIN_EFF
    rho = vehicle.air_density_kg_m3 if vehicle.air_density_kg_m3 is not None else DEFAULT_RHO
    crr = vehicle.crr if vehicle.crr is not None else DEFAULT_CRR

    best_speed_kph = 0.0
    best_gear = 0
    best_rpm = 0.0

    for gi, gr in enumerate(drivetrain.gears, start=1):
        for rpm, p_kw in zip(rpms, power_kw):
            if rpm > rpm_cap:
                continue
            v_mps = speed_mps_from_rpm(rpm, gr, drivetrain.final_drive, drivetrain.tire_radius_m)
            p_avail_w = (p_kw * 1000.0) * eff
            p_req_w = road_load_power_w(
                v_mps,
                mass_kg=vehicle.mass_kg,
                cd=vehicle.cd,
                frontal_area_m2=vehicle.frontal_area_m2,
                crr=crr,
                air_density_kg_m3=rho,
            )
            if p_avail_w >= p_req_w:
                v_kph = v_mps * 3.6
                if v_kph > best_speed_kph:
                    best_speed_kph = v_kph
                    best_gear = gi
                    best_rpm = rpm

    return {
        "top_speed_kph": best_speed_kph,
        "top_speed_gear": float(best_gear),
        "top_speed_rpm": float(best_rpm),
        "drivetrain_eff": float(eff),
        "rho": float(rho),
        "crr": float(crr),
    }
