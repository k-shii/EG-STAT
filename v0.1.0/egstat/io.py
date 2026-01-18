from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import json
from typing import Optional, Any
from egstat.models import EngineSpec, Assumptions, RunConfig, VehicleSpec, DrivetrainSpec, Result
from egstat.vehicle import speed_kph_from_rpm


@dataclass
class RunFile:
    version: str
    engine: EngineSpec
    assumptions: Assumptions
    run_config: RunConfig
    peak_bmep_kpa: float | None = None
    vehicle: VehicleSpec | None = None
    drivetrain: DrivetrainSpec | None = None
    result: Result | None = None


def _ensure_parent_dir(p: Path) -> None:
    # Create parent dirs for output paths like runs/out/foo.json
    if p.parent and str(p.parent) not in ("", "."):
        p.parent.mkdir(parents=True, exist_ok=True)


def save_run_json(path: str | Path, run: RunFile) -> None:
    p = Path(path)
    _ensure_parent_dir(p)

    payload = {
        "version": run.version,
        "inputs": {
            "engine": run.engine.to_dict(),
            "assumptions": run.assumptions.to_dict(),
            "run_config": run.run_config.to_dict(),
            "peak_bmep_kpa": run.peak_bmep_kpa,
            "vehicle": run.vehicle.to_dict() if run.vehicle is not None else None,
            "drivetrain": run.drivetrain.to_dict() if run.drivetrain is not None else None,
        },
        "result": run.result.to_dict() if run.result is not None else None,
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_run_json(path: str | Path) -> RunFile:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))

    inputs = payload.get("inputs", {})
    engine = EngineSpec.from_dict(inputs["engine"])
    assumptions = Assumptions.from_dict(inputs["assumptions"])
    run_config = RunConfig.from_dict(inputs["run_config"])

    vehicle_data = inputs.get("vehicle")
    drivetrain_data = inputs.get("drivetrain")

    vehicle = VehicleSpec.from_dict(vehicle_data) if vehicle_data else None
    drivetrain = DrivetrainSpec.from_dict(drivetrain_data) if drivetrain_data else None

    result_data = payload.get("result")
    result = Result.from_dict(result_data) if result_data else None

    return RunFile(
        version=str(payload.get("version", "unknown")),
        engine=engine,
        assumptions=assumptions,
        run_config=run_config,
        peak_bmep_kpa=inputs.get("peak_bmep_kpa"),
        vehicle=vehicle,
        drivetrain=drivetrain,
        result=result,
    )


def export_curves_csv(
    path: str | Path,
    result: Result,
    drivetrain: DrivetrainSpec | None = None,
) -> None:
    p = Path(path)
    _ensure_parent_dir(p)

    rpms = result.curves.get("rpm", [])
    tq = result.curves.get("torque_nm", [])
    pw = result.curves.get("power_kw", [])
    bmep = result.curves.get("bmep_kpa", [])

    n = min(len(rpms), len(tq), len(pw), len(bmep))
    rpms = rpms[:n]
    tq = tq[:n]
    pw = pw[:n]
    bmep = bmep[:n]

    gear_cols: list[str] = []
    speeds_by_gear: list[list[float]] = []

    if (
        drivetrain is not None
        and drivetrain.gears is not None
        and drivetrain.final_drive is not None
        and drivetrain.tire_radius_m is not None
    ):
        for gi, gr in enumerate(drivetrain.gears, start=1):
            gear_cols.append(f"speed_kph_g{gi}")
            speeds_by_gear.append(
                [
                    float(speed_kph_from_rpm(float(r), gr, drivetrain.final_drive, drivetrain.tire_radius_m))
                    for r in rpms
                ]
            )

    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["rpm", "bmep_kpa", "torque_nm", "power_kw"] + gear_cols
        w.writerow(header)

        for i in range(n):
            row = [float(rpms[i]), float(bmep[i]), float(tq[i]), float(pw[i])]
            for sg in speeds_by_gear:
                row.append(float(sg[i]))
            w.writerow(row)


def export_candidates_csv(path: str | Path, candidates: list[dict[str, Any]]) -> None:
    """
    Export design candidates. Keeps this function intentionally tolerant:
    - candidates is a list of dicts, commonly with keys: score, engine, assumptions, run_config, peak_bmep_kpa, result
    - engine is an EngineSpec
    - result is a Result
    """
    p = Path(path)
    _ensure_parent_dir(p)

    # Header is stable even if some fields are missing
    header = [
        "rank",
        "score",
        "disp_cc",
        "cyl",
        "cycle",
        "redline_rpm",
        "peak_bmep_kpa",
        "ve_profile",
        "fuel",
        "bsfc_g_per_kwh",
        "peak_power_kw",
        "peak_power_rpm",
        "peak_torque_nm",
        "peak_torque_rpm",
    ]

    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)

        for i, c in enumerate(candidates, start=1):
            engine = c.get("engine")
            assumptions = c.get("assumptions")
            peak_bmep_kpa = c.get("peak_bmep_kpa")
            res = c.get("result")
            scalars = getattr(res, "scalars", {}) if res is not None else {}

            # Try to get displacement in cc from engine (robust against implementation differences)
            disp_cc = None
            if engine is not None:
                # preferred: engine.displacement_m3 (convert to cc)
                dm3 = getattr(engine, "displacement_m3", None)
                if dm3 is not None:
                    try:
                        disp_cc = float(dm3) * 1_000_000.0
                    except Exception:
                        disp_cc = None

            w.writerow([
                i,
                c.get("score"),
                disp_cc,
                getattr(engine, "cylinders", None) if engine is not None else None,
                getattr(engine, "cycle", None) if engine is not None else None,
                getattr(engine, "redline_rpm", None) if engine is not None else None,
                peak_bmep_kpa,
                getattr(assumptions, "ve_profile", None) if assumptions is not None else None,
                getattr(assumptions, "fuel", None) if assumptions is not None else None,
                getattr(assumptions, "bsfc_g_per_kwh", None) if assumptions is not None else None,
                scalars.get("peak_power_kw"),
                scalars.get("peak_power_rpm"),
                scalars.get("peak_torque_nm"),
                scalars.get("peak_torque_rpm"),
            ])
