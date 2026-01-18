from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from egstat.models import Assumptions, VehicleSpec, DrivetrainSpec


@dataclass(frozen=True)
class PresetInfo:
    name: str
    description: str


# --- Engine/assumption presets (minimal but useful) ---
ENGINE_PRESETS: dict[str, dict[str, Any]] = {
    "na_street": {
        "ve_profile": "balanced",
        "fuel": "petrol",
        "bsfc_g_per_kwh": None,
        "description": "Naturally aspirated street engine (balanced curve, petrol BSFC default)",
    },
    "na_torque": {
        "ve_profile": "torque_biased",
        "fuel": "petrol",
        "bsfc_g_per_kwh": None,
        "description": "NA torque-biased (earlier peak, petrol BSFC default)",
    },
    "turbo_sport": {
        "ve_profile": "top_end",
        "fuel": "petrol",
        "bsfc_g_per_kwh": 290.0,
        "description": "Sport turbo-ish assumptions (top-end curve, slightly worse BSFC)",
    },
    "diesel_torque": {
        "ve_profile": "torque_biased",
        "fuel": "diesel",
        "bsfc_g_per_kwh": None,
        "description": "Diesel torque assumptions (diesel BSFC default)",
    },
    "e85_performance": {
        "ve_profile": "top_end",
        "fuel": "e85",
        "bsfc_g_per_kwh": None,
        "description": "E85 performance assumptions (higher BSFC default)",
    },
}


VEHICLE_PRESETS: dict[str, dict[str, Any]] = {
    "hatch": {
        "mass_kg": 1200.0,
        "cd": 0.30,
        "frontal_area_m2": 2.1,
        "crr": 0.012,
        "air_density_kg_m3": 1.225,
        "description": "Small hatchback baseline",
    },
    "sedan": {
        "mass_kg": 1500.0,
        "cd": 0.29,
        "frontal_area_m2": 2.2,
        "crr": 0.012,
        "air_density_kg_m3": 1.225,
        "description": "Mid-size sedan baseline",
    },
    "suv": {
        "mass_kg": 1900.0,
        "cd": 0.34,
        "frontal_area_m2": 2.6,
        "crr": 0.013,
        "air_density_kg_m3": 1.225,
        "description": "SUV baseline (bigger CdA + mass)",
    },
    "brick4wd": {
        "mass_kg": 2400.0,
        "cd": 0.40,
        "frontal_area_m2": 3.0,
        "crr": 0.014,
        "air_density_kg_m3": 1.225,
        "description": "Big 4WD brick (worst aero)",
    },
}


GEARBOX_PRESETS: dict[str, dict[str, Any]] = {
    "6mt_typical": {
        "gears": [3.60, 2.19, 1.41, 1.12, 0.87, 0.69],
        "final_drive": 4.10,
        "tire_radius_m": 0.31,
        "drivetrain_efficiency": 0.90,
        "description": "Typical 6MT ratios + 4.10 final + 0.31m tire",
    },
    "5mt_short": {
        "gears": [3.55, 1.95, 1.29, 0.97, 0.78],
        "final_drive": 4.30,
        "tire_radius_m": 0.31,
        "drivetrain_efficiency": 0.90,
        "description": "Short 5MT (more acceleration oriented)",
    },
    "8at_typical": {
        "gears": [4.71, 3.14, 2.11, 1.67, 1.29, 1.00, 0.84, 0.67],
        "final_drive": 3.15,
        "tire_radius_m": 0.31,
        "drivetrain_efficiency": 0.88,
        "description": "Typical 8AT ratios",
    },
}


def list_engine_presets() -> list[str]:
    return sorted(ENGINE_PRESETS.keys())


def list_vehicle_presets() -> list[str]:
    return sorted(VEHICLE_PRESETS.keys())


def list_gearbox_presets() -> list[str]:
    return sorted(GEARBOX_PRESETS.keys())


def apply_engine_preset(preset: str, base: Assumptions | None = None) -> Assumptions:
    if preset not in ENGINE_PRESETS:
        raise ValueError(f"Unknown engine preset '{preset}'. Valid: {list_engine_presets()}")
    d = ENGINE_PRESETS[preset]
    a = base if base is not None else Assumptions()
    # explicit overwrite from preset
    a.ve_profile = d["ve_profile"]
    a.fuel = d["fuel"]
    a.bsfc_g_per_kwh = d["bsfc_g_per_kwh"]
    return a


def apply_vehicle_preset(preset: str, base: VehicleSpec | None = None) -> VehicleSpec:
    if preset not in VEHICLE_PRESETS:
        raise ValueError(f"Unknown vehicle preset '{preset}'. Valid: {list_vehicle_presets()}")
    d = VEHICLE_PRESETS[preset]
    v = base if base is not None else VehicleSpec()
    v.mass_kg = d["mass_kg"]
    v.cd = d["cd"]
    v.frontal_area_m2 = d["frontal_area_m2"]
    v.crr = d["crr"]
    v.air_density_kg_m3 = d["air_density_kg_m3"]
    return v


def apply_gearbox_preset(preset: str, base: DrivetrainSpec | None = None) -> DrivetrainSpec:
    if preset not in GEARBOX_PRESETS:
        raise ValueError(f"Unknown gearbox preset '{preset}'. Valid: {list_gearbox_presets()}")
    d = GEARBOX_PRESETS[preset]
    g = base if base is not None else DrivetrainSpec()
    g.gears = list(d["gears"])
    g.final_drive = d["final_drive"]
    g.tire_radius_m = d["tire_radius_m"]
    g.drivetrain_efficiency = d["drivetrain_efficiency"]
    return g
