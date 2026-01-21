from __future__ import annotations
import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from egstat.models import EngineSpec, Assumptions, RunConfig, VehicleSpec, DrivetrainSpec, Result
from egstat.performance import analyze_basic_curves
from egstat.units import mm_to_m, cc_to_m3
from egstat.curves import list_profiles
from egstat.vehicle import per_gear_redline_speeds_kph, estimate_top_speed
from egstat.shifts import recommend_upshifts
from egstat.presets import (
    ENGINE_PRESETS,
    VEHICLE_PRESETS,
    GEARBOX_PRESETS,
    list_engine_presets,
    list_vehicle_presets,
    list_gearbox_presets,
    apply_engine_preset,
    apply_vehicle_preset,
    apply_gearbox_preset,
)
from egstat.io import RunFile, save_run_json, load_run_json, export_curves_csv, export_candidates_csv
from egstat.solver import match_engine
from egstat import ui

APP_VERSION = "0.2.1"
LEGACY_SUBCOMMANDS = {"analyze", "match", "design"}
NONINTERACTIVE_TEST_ENV = "EGSTAT_NONINTERACTIVE_TEST"
NONINTERACTIVE_TEST_MARKER = "Interactive mode started"


@dataclass
class RunData:
    engine: EngineSpec
    assumptions: Assumptions
    run_config: RunConfig
    peak_bmep_kpa: float | None
    vehicle: VehicleSpec | None
    drivetrain: DrivetrainSpec | None
    result: Result


@dataclass
class MatchMeta:
    confidence: float
    assumptions_made: list[str]


def _sorted_preset_list(presets: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    items = []
    for name in sorted(presets.keys()):
        desc = presets[name].get("description", "")
        items.append((name, desc))
    return items


def _normalize_save_path(raw: str | None, expected_ext: str) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip().strip("\"'").strip()
    cleaned = cleaned.rstrip(" .")
    if not cleaned:
        return None
    expected = expected_ext if expected_ext.startswith(".") else f".{expected_ext}"
    suffix = ""
    try:
        suffix = Path(cleaned).suffix
    except Exception:
        suffix = ""
    if not suffix:
        return f"{cleaned}{expected}"
    if suffix.lower() != expected.lower():
        print(f"ERROR: Path must end with '{expected}'.")
        return None
    return cleaned


def _prompt_save_path(label: str, default_name: str, expected_ext: str) -> str | None:
    while True:
        raw = ui.prompt_text(f"{label} (default {default_name}, blank to cancel)", default=None, allow_empty=True)
        if raw is None:
            return None
        normalized = _normalize_save_path(raw, expected_ext)
        if normalized is not None:
            return normalized


def _compute_analyze(args: argparse.Namespace) -> RunData | None:
    loaded = None
    veh = None
    drv = None
    peak_bmep_kpa = None

    if args.load_json:
        loaded = load_run_json(args.load_json)
        engine = loaded.engine
        assumptions = loaded.assumptions
        cfg = loaded.run_config
        peak_bmep_kpa = loaded.peak_bmep_kpa
        veh = loaded.vehicle
        drv = loaded.drivetrain

        if loaded.result is not None and not args.recompute:
            res = loaded.result
        else:
            if peak_bmep_kpa is None:
                print("ERROR: Loaded JSON missing peak_bmep_kpa; cannot recompute.")
                return None
            res = analyze_basic_curves(engine, assumptions, cfg, peak_bmep_kpa=peak_bmep_kpa)

    else:
        if args.peak_bmep_kpa is None:
            print("ERROR: --peak-bmep-kpa is required unless --load-json is used.")
            return None

        if args.disp_cc is None and (args.bore_mm is None or args.stroke_mm is None or args.cyl is None):
            print("ERROR: Provide either --disp-cc OR (--cyl + --bore-mm + --stroke-mm).")
            return None

        engine = EngineSpec(
            cylinders=args.cyl if args.cyl is not None else 4,
            cycle=args.cycle,
            bore_m=mm_to_m(args.bore_mm) if args.bore_mm is not None else None,
            stroke_m=mm_to_m(args.stroke_mm) if args.stroke_mm is not None else None,
            displacement_m3=cc_to_m3(args.disp_cc) if args.disp_cc is not None else None,
            idle_rpm=args.idle,
            redline_rpm=args.redline,
        )

        assumptions = Assumptions(ve_profile=args.profile, fuel=args.fuel, bsfc_g_per_kwh=args.bsfc)

        if args.engine_preset:
            assumptions = apply_engine_preset(args.engine_preset, assumptions)

        assumptions.ve_profile = args.profile
        assumptions.fuel = args.fuel
        assumptions.bsfc_g_per_kwh = args.bsfc

        cfg = RunConfig(rpm_min=args.rpm_min, rpm_max=args.rpm_max, rpm_step=args.rpm_step)
        peak_bmep_kpa = args.peak_bmep_kpa

        res = analyze_basic_curves(
            engine,
            assumptions,
            cfg,
            peak_bmep_kpa=peak_bmep_kpa,
        )

    if res.issues and any(s.startswith("[ERROR]") for s in res.issues):
        for s in res.issues:
            print(s)
        return None

    if not res.curves:
        for s in res.issues:
            print(s)
        if not res.issues:
            print("ERROR: No output produced.")
        return None

    have_vehicle = (veh is not None) or (args.vehicle_preset is not None) or (
        args.mass_kg is not None and args.cd is not None and args.fa_m2 is not None
    )
    have_drive = (drv is not None) or (args.gearbox_preset is not None) or (
        args.gears is not None and args.final_drive is not None and args.tire_radius_m is not None
    )

    if have_vehicle and have_drive:
        if veh is None:
            veh = VehicleSpec(
                mass_kg=args.mass_kg,
                cd=args.cd,
                frontal_area_m2=args.fa_m2,
                crr=args.crr,
                air_density_kg_m3=args.rho,
            )
        if drv is None:
            drv = DrivetrainSpec(
                gears=args.gears,
                final_drive=args.final_drive,
                tire_radius_m=args.tire_radius_m,
                drivetrain_efficiency=args.drivetrain_eff,
            )

        if args.vehicle_preset:
            veh = apply_vehicle_preset(args.vehicle_preset, veh)
        if args.gearbox_preset:
            drv = apply_gearbox_preset(args.gearbox_preset, drv)

        if args.mass_kg is not None:
            veh.mass_kg = args.mass_kg
        if args.cd is not None:
            veh.cd = args.cd
        if args.fa_m2 is not None:
            veh.frontal_area_m2 = args.fa_m2
        if args.crr is not None:
            veh.crr = args.crr
        if args.rho is not None:
            veh.air_density_kg_m3 = args.rho

        if args.gears is not None:
            drv.gears = args.gears
        if args.final_drive is not None:
            drv.final_drive = args.final_drive
        if args.tire_radius_m is not None:
            drv.tire_radius_m = args.tire_radius_m
        if args.drivetrain_eff is not None:
            drv.drivetrain_efficiency = args.drivetrain_eff

    return RunData(
        engine=engine,
        assumptions=assumptions,
        run_config=cfg,
        peak_bmep_kpa=peak_bmep_kpa,
        vehicle=veh,
        drivetrain=drv,
        result=res,
    )


def _compute_match(args: argparse.Namespace) -> tuple[RunData | None, MatchMeta | None]:
    engine = EngineSpec(
        cylinders=args.cyl if args.cyl is not None else 0,
        cycle=args.cycle,
        bore_m=mm_to_m(args.bore_mm) if args.bore_mm is not None else None,
        stroke_m=mm_to_m(args.stroke_mm) if args.stroke_mm is not None else None,
        displacement_m3=cc_to_m3(args.disp_cc) if args.disp_cc is not None else None,
        idle_rpm=args.idle,
        redline_rpm=args.redline,
    )

    assumptions = Assumptions(ve_profile=args.profile, fuel=args.fuel, bsfc_g_per_kwh=args.bsfc)

    if args.engine_preset:
        assumptions = apply_engine_preset(args.engine_preset, assumptions)

    assumptions.ve_profile = args.profile
    assumptions.fuel = args.fuel
    assumptions.bsfc_g_per_kwh = args.bsfc

    m = match_engine(
        engine,
        assumptions,
        target_power_kw=args.target_power_kw,
        target_power_rpm=args.target_power_rpm,
        target_torque_nm=args.target_torque_nm,
        target_torque_rpm=args.target_torque_rpm,
        peak_bmep_kpa=args.peak_bmep_kpa,
    )

    cfg = RunConfig(rpm_min=args.rpm_min, rpm_max=args.rpm_max, rpm_step=args.rpm_step)
    res = analyze_basic_curves(m.engine, assumptions, cfg, peak_bmep_kpa=m.peak_bmep_kpa)

    if res.issues and any(s.startswith("[ERROR]") for s in res.issues):
        for s in res.issues:
            print(s)
        return None, None

    if not res.curves:
        for s in res.issues:
            print(s)
        if not res.issues:
            print("ERROR: No output produced.")
        return None, None

    run = RunData(
        engine=m.engine,
        assumptions=assumptions,
        run_config=cfg,
        peak_bmep_kpa=m.peak_bmep_kpa,
        vehicle=None,
        drivetrain=None,
        result=res,
    )
    meta = MatchMeta(confidence=m.confidence, assumptions_made=list(m.assumptions_made))
    return run, meta


def _render_run_sections(run: RunData) -> None:
    res = run.result
    disp_l = res.scalars.get("displacement_l")
    if disp_l is None and run.engine.displacement_m3 is not None:
        disp_l = float(run.engine.displacement_m3) * 1000.0

    ui.print_section("Inputs")
    if disp_l is not None:
        ui.print_kv("Displacement", f"{disp_l:.3f} L")
    ui.print_kv(
        "Engine",
        f"{run.engine.cylinders} cyl, {run.engine.cycle}, idle {run.engine.idle_rpm} rpm, redline {run.engine.redline_rpm} rpm",
    )
    if run.engine.bore_m is not None and run.engine.stroke_m is not None:
        ui.print_kv(
            "Bore x Stroke",
            f"{run.engine.bore_m * 1000.0:.1f} x {run.engine.stroke_m * 1000.0:.1f} mm",
        )
    if run.peak_bmep_kpa is not None:
        ui.print_kv("Peak BMEP", f"{float(run.peak_bmep_kpa):.1f} kPa")
    ui.print_kv(
        "RPM sweep",
        f"{run.run_config.rpm_min}-{run.run_config.rpm_max} rpm (step {run.run_config.rpm_step})",
    )

    ui.print_section("Results")
    print(f"Peak torque: {res.scalars['peak_torque_nm']:.1f} Nm @ {int(res.scalars['peak_torque_rpm'])} rpm")
    print(f"Peak power:  {res.scalars['peak_power_kw']:.1f} kW @ {int(res.scalars['peak_power_rpm'])} rpm")
    print(f"Fuel @ peak power (WOT): {res.scalars['fuel_wot_lph_at_peak_power']:.1f} L/h")
    print(f"Fuel @ 20 kW cruise est: {res.scalars['fuel_cruise_lph_at_20kw']:.1f} L/h")
    if "piston_speed_mps_at_redline" in res.scalars:
        print(f"Piston speed @ redline: {res.scalars['piston_speed_mps_at_redline']:.2f} m/s")

    ui.print_section("Assumptions")
    ui.print_kv("Profile", run.assumptions.ve_profile)
    ui.print_kv("Fuel", run.assumptions.fuel)
    bsfc = res.scalars.get("bsfc_g_per_kwh")
    if bsfc is not None:
        ui.print_kv("BSFC", f"{bsfc:.0f} g/kWh")

    if res.issues:
        ui.print_section("Warnings/Issues")
        for s in res.issues:
            print(f"- {s}")


def _render_vehicle_outputs(run: RunData) -> None:
    if run.vehicle is None or run.drivetrain is None:
        return
    veh = run.vehicle
    drv = run.drivetrain

    ui.print_section("Vehicle/Drivetrain")
    if veh.mass_kg is not None:
        ui.print_kv("Mass", f"{veh.mass_kg:.1f} kg")
    if veh.cd is not None:
        ui.print_kv("Cd", f"{veh.cd:.3f}")
    if veh.frontal_area_m2 is not None:
        ui.print_kv("Frontal area", f"{veh.frontal_area_m2:.2f} m^2")
    if veh.crr is not None:
        ui.print_kv("Crr", f"{veh.crr:.4f}")
    if veh.air_density_kg_m3 is not None:
        ui.print_kv("Air density", f"{veh.air_density_kg_m3:.3f} kg/m^3")

    speeds = per_gear_redline_speeds_kph(run.engine, drv)
    print("Gear speeds @ redline:")
    for i, skph in enumerate(speeds, start=1):
        print(f"  Gear {i}: {skph:.1f} km/h")

    ts = estimate_top_speed(run.result, run.engine, veh, drv)
    print(f"Top speed est: {ts['top_speed_kph']:.1f} km/h  (gear {int(ts['top_speed_gear'])} @ {int(ts['top_speed_rpm'])} rpm)")
    print(f"Assumptions: crr={ts['crr']:.4f}, rho={ts['rho']:.3f}, drivetrain_eff={ts['drivetrain_eff']:.2f}")

    ups = recommend_upshifts(run.result, run.engine, drv)
    print("Upshift suggestions:")
    for u in ups:
        if "speed_kph_at_shift" in u:
            print(f"  {int(u['from_gear'])}->{int(u['to_gear'])}: {int(u['upshift_rpm'])} rpm (drops to {int(u['post_shift_rpm'])}) @ {u['speed_kph_at_shift']:.1f} km/h")
        else:
            print(f"  {int(u['from_gear'])}->{int(u['to_gear'])}: {int(u['upshift_rpm'])} rpm (drops to {int(u['post_shift_rpm'])})")


def _render_ascii(run: RunData, ascii_step: int) -> None:
    ui.print_section("ASCII Table")
    ui.render_ascii_table(run.result.curves, ascii_step)
    ui.print_section("ASCII Curves")
    ui.render_ascii_curves(run.result.curves, ascii_step)


def _prompt_post_run_io(
    run: RunData,
    *,
    allow_export_curves: bool,
    allow_export_candidates: bool = False,
    candidates: list[dict[str, Any]] | None = None,
) -> None:
    if ui.prompt_yes_no("Save run JSON?", default=False):
        path = _prompt_save_path("Save JSON path", "run.json", ".json")
        if path is not None:
            run_file = RunFile(
                version="0.0.1",
                engine=run.engine,
                assumptions=run.assumptions,
                run_config=run.run_config,
                peak_bmep_kpa=run.peak_bmep_kpa,
                vehicle=run.vehicle,
                drivetrain=run.drivetrain,
                result=run.result,
            )
            save_run_json(path, run_file)
            print(f"Saved JSON: {path}")

    if allow_export_curves and ui.prompt_yes_no("Export curves CSV?", default=False):
        path = _prompt_save_path("Export CSV path", "curves.csv", ".csv")
        if path is not None:
            export_curves_csv(path, run.result, run.drivetrain)
            print(f"Exported CSV: {path}")

    if allow_export_candidates and candidates is not None:
        if ui.prompt_yes_no("Export candidates CSV?", default=False):
            path = _prompt_save_path("Export candidates CSV path", "candidates.csv", ".csv")
            if path is not None:
                export_candidates_csv(path, candidates)
                print(f"Exported candidates CSV: {path}")


def cmd_analyze(args: argparse.Namespace) -> int:
    run = _compute_analyze(args)
    if run is None:
        return 2

    _render_run_sections(run)
    _render_vehicle_outputs(run)

    if args.ascii:
        _render_ascii(run, args.ascii_step)

    if args.export_csv:
        path = _normalize_save_path(args.export_csv, ".csv")
        if path is None:
            return 2
        export_curves_csv(path, run.result, run.drivetrain)
        print(f"\nExported CSV: {path}")

    if args.save_json:
        path = _normalize_save_path(args.save_json, ".json")
        if path is None:
            return 2
        run_file = RunFile(
            version="0.0.1",
            engine=run.engine,
            assumptions=run.assumptions,
            run_config=run.run_config,
            peak_bmep_kpa=run.peak_bmep_kpa,
            vehicle=run.vehicle,
            drivetrain=run.drivetrain,
            result=run.result,
        )
        save_run_json(path, run_file)
        print(f"Saved JSON: {path}")

    return 0


def cmd_match(args: argparse.Namespace) -> int:
    run, meta = _compute_match(args)
    if run is None or meta is None:
        return 2

    print("Mode: match")
    print(f"Confidence: {meta.confidence:.2f}")
    if meta.assumptions_made:
        print("Assumptions made:")
        for s in meta.assumptions_made:
            print(" ", s)

    _render_run_sections(run)

    if args.ascii:
        _render_ascii(run, args.ascii_step)

    if args.export_csv:
        path = _normalize_save_path(args.export_csv, ".csv")
        if path is None:
            return 2
        export_curves_csv(path, run.result, None)
        print(f"\nExported CSV: {path}")

    if args.save_json:
        path = _normalize_save_path(args.save_json, ".json")
        if path is None:
            return 2
        run_file = RunFile(
            version="0.0.1",
            engine=run.engine,
            assumptions=run.assumptions,
            run_config=run.run_config,
            peak_bmep_kpa=run.peak_bmep_kpa,
            vehicle=None,
            drivetrain=None,
            result=run.result,
        )
        save_run_json(path, run_file)
        print(f"Saved JSON: {path}")

    return 0


def cmd_design(args: argparse.Namespace) -> int:
    from dataclasses import asdict, is_dataclass
    from egstat.solver import design_candidates

    cands = design_candidates(
        target_power_kw=args.target_power_kw,
        target_power_rpm=args.target_power_rpm,
        redline_rpm=args.redline,
        profile=args.profile,
        cycle=getattr(args, "cycle", "4-stroke"),
        fuel=args.fuel,
        bsfc_g_per_kwh=getattr(args, "bsfc", None),
        bmep_max_kpa=args.bmep_max_kpa,
        piston_speed_max_mps=args.piston_speed_max,
        disp_min_cc=args.disp_min_cc,
        disp_max_cc=args.disp_max_cc,
        disp_step_cc=args.disp_step_cc,
        cylinders_list=args.cyls,
        top_n=args.top_n,
    )

    print("Mode: design")
    if not cands:
        print("No candidates found.")
        return 2

    print(f"Candidates: {len(cands)}")

    best = cands[0]
    print(f"Best score: {best.score:.3f}")

    run = RunData(
        engine=best.engine,
        assumptions=best.assumptions,
        run_config=best.run_config,
        peak_bmep_kpa=best.peak_bmep_kpa,
        vehicle=None,
        drivetrain=None,
        result=best.result,
    )

    _render_run_sections(run)

    if args.ascii:
        _render_ascii(run, args.ascii_step)

    if getattr(args, "export_candidates_csv", None):
        path = _normalize_save_path(args.export_candidates_csv, ".csv")
        if path is None:
            return 2
        cands_export = [asdict(c) if is_dataclass(c) else c for c in cands]
        export_candidates_csv(path, cands_export)
        print(f"Exported candidates CSV: {path}")

    if getattr(args, "save_json", None):
        path = _normalize_save_path(args.save_json, ".json")
        if path is None:
            return 2
        run_file = RunFile(
            version="0.0.1",
            engine=best.engine,
            assumptions=best.assumptions,
            run_config=best.run_config,
            peak_bmep_kpa=best.peak_bmep_kpa,
            vehicle=None,
            drivetrain=None,
            result=best.result,
        )
        save_run_json(path, run_file)
        print(f"Saved JSON: {path}")

    return 0


def _should_guided_analyze(args: argparse.Namespace) -> bool:
    if not ui.is_interactive():
        return False
    if args.load_json:
        return False
    missing_bmep = args.peak_bmep_kpa is None
    missing_disp = args.disp_cc is None and (args.bore_mm is None or args.stroke_mm is None or args.cyl is None)
    return missing_bmep or missing_disp


def _should_guided_match(args: argparse.Namespace) -> bool:
    if not ui.is_interactive():
        return False
    has_target = any(
        v is not None
        for v in (
            args.target_power_kw,
            args.target_torque_nm,
            args.peak_bmep_kpa,
        )
    )
    return not has_target


def _should_guided_design(args: argparse.Namespace) -> bool:
    if not ui.is_interactive():
        return False
    return args.target_power_kw is None


def _guided_analyze(defaults: argparse.Namespace | None = None) -> int:
    print("Guided mode: Analyze")
    engine_preset = ui.prompt_preset("Engine preset", _sorted_preset_list(ENGINE_PRESETS))

    assumptions = Assumptions()
    if engine_preset:
        assumptions = apply_engine_preset(engine_preset, assumptions)

    use_disp = ui.prompt_yes_no("Use displacement (cc) input?", default=True)
    if use_disp:
        disp_cc = ui.prompt_float("Displacement (cc)", default=1998.0, min_value=1.0)
        cyl = ui.prompt_int("Cylinders", default=4, min_value=1)
        bore_mm = None
        stroke_mm = None
    else:
        cyl = ui.prompt_int("Cylinders", default=4, min_value=1)
        bore_mm = ui.prompt_float("Bore (mm)", default=86.0, min_value=1.0)
        stroke_mm = ui.prompt_float("Stroke (mm)", default=86.0, min_value=1.0)
        disp_cc = None

    cycle = ui.prompt_choice("Cycle", ["4-stroke", "2-stroke"], default="4-stroke")
    idle = ui.prompt_int("Idle rpm", default=800, min_value=1)
    redline = ui.prompt_int("Redline rpm", default=7000, min_value=1)
    peak_bmep_kpa = ui.prompt_float("Peak BMEP (kPa)", default=1000.0, min_value=1.0)

    profile = ui.prompt_choice("VE profile", list_profiles(), default=assumptions.ve_profile)
    fuel = ui.prompt_choice("Fuel", ["petrol", "diesel", "e85"], default=assumptions.fuel)
    bsfc = ui.prompt_float("BSFC g/kWh (blank for auto)", default=assumptions.bsfc_g_per_kwh, allow_empty=True)

    rpm_min = ui.prompt_int("RPM min", default=1000, min_value=1)
    rpm_max = ui.prompt_int("RPM max", default=redline, min_value=rpm_min)
    rpm_step = ui.prompt_int("RPM step", default=100, min_value=1)

    vehicle_preset = None
    gearbox_preset = None
    mass_kg = cd = fa_m2 = crr = rho = None
    gears = final_drive = tire_radius_m = drivetrain_eff = None

    if ui.prompt_yes_no("Add vehicle + drivetrain inputs?", default=False):
        vehicle_preset = ui.prompt_preset("Vehicle preset", _sorted_preset_list(VEHICLE_PRESETS))
        veh = VehicleSpec()
        if vehicle_preset:
            veh = apply_vehicle_preset(vehicle_preset, veh)
        mass_kg = ui.prompt_float("Mass (kg)", default=veh.mass_kg or 1500.0, min_value=1.0)
        cd = ui.prompt_float("Cd", default=veh.cd or 0.29, min_value=0.01)
        fa_m2 = ui.prompt_float("Frontal area (m^2)", default=veh.frontal_area_m2 or 2.2, min_value=0.1)
        crr = ui.prompt_float("Crr", default=veh.crr or 0.012, min_value=0.001)
        rho = ui.prompt_float("Air density (kg/m^3)", default=veh.air_density_kg_m3 or 1.225, min_value=0.1)

        gearbox_preset = ui.prompt_preset("Gearbox preset", _sorted_preset_list(GEARBOX_PRESETS))
        drv = DrivetrainSpec()
        if gearbox_preset:
            drv = apply_gearbox_preset(gearbox_preset, drv)
        gears = ui.prompt_float_list("Gear ratios", default=drv.gears or [3.6, 2.19, 1.41, 1.12, 0.87, 0.69])
        final_drive = ui.prompt_float("Final drive", default=drv.final_drive or 4.1, min_value=0.1)
        tire_radius_m = ui.prompt_float("Tire radius (m)", default=drv.tire_radius_m or 0.31, min_value=0.1)
        drivetrain_eff = ui.prompt_float("Drivetrain efficiency (0-1)", default=drv.drivetrain_efficiency or 0.90, min_value=0.1, max_value=1.0)

    ascii_step = ui.prompt_int("ASCII sample step (rpm)", default=500, min_value=1)

    args = SimpleNamespace(
        load_json=None,
        recompute=False,
        disp_cc=disp_cc,
        cyl=cyl,
        bore_mm=bore_mm,
        stroke_mm=stroke_mm,
        cycle=cycle,
        idle=idle,
        redline=redline,
        peak_bmep_kpa=peak_bmep_kpa,
        profile=profile,
        rpm_min=rpm_min,
        rpm_max=rpm_max,
        rpm_step=rpm_step,
        fuel=fuel,
        bsfc=bsfc,
        engine_preset=engine_preset,
        vehicle_preset=vehicle_preset,
        gearbox_preset=gearbox_preset,
        mass_kg=mass_kg,
        cd=cd,
        fa_m2=fa_m2,
        crr=crr,
        rho=rho,
        drivetrain_eff=drivetrain_eff,
        final_drive=final_drive,
        tire_radius_m=tire_radius_m,
        gears=gears,
        export_csv=None,
        save_json=None,
        ascii=True,
        ascii_step=ascii_step,
    )

    run = _compute_analyze(args)
    if run is None:
        return 2

    _render_run_sections(run)
    _render_vehicle_outputs(run)
    _render_ascii(run, ascii_step)
    _prompt_post_run_io(run, allow_export_curves=True)
    return 0


def _guided_match(defaults: argparse.Namespace | None = None) -> int:
    print("Guided mode: Match")
    engine_preset = ui.prompt_preset("Engine preset", _sorted_preset_list(ENGINE_PRESETS))

    assumptions = Assumptions()
    if engine_preset:
        assumptions = apply_engine_preset(engine_preset, assumptions)

    disp_cc = ui.prompt_float("Displacement (cc) [optional]", allow_empty=True)
    cyl = ui.prompt_int("Cylinders [optional]", allow_empty=True, min_value=1)
    bore_mm = ui.prompt_float("Bore (mm) [optional]", allow_empty=True, min_value=1.0)
    stroke_mm = ui.prompt_float("Stroke (mm) [optional]", allow_empty=True, min_value=1.0)

    cycle = ui.prompt_choice("Cycle", ["4-stroke", "2-stroke"], default="4-stroke")
    idle = ui.prompt_int("Idle rpm", default=800, min_value=1)
    redline = ui.prompt_int("Redline rpm", default=7000, min_value=1)

    profile = ui.prompt_choice("VE profile", list_profiles(), default=assumptions.ve_profile)
    fuel = ui.prompt_choice("Fuel", ["petrol", "diesel", "e85"], default=assumptions.fuel)
    bsfc = ui.prompt_float("BSFC g/kWh (blank for auto)", default=assumptions.bsfc_g_per_kwh, allow_empty=True)

    target_power_kw = ui.prompt_float("Target power (kW) [optional]", allow_empty=True, min_value=1.0)
    target_power_rpm = ui.prompt_int("Target power rpm [optional]", allow_empty=True, min_value=1)
    target_torque_nm = ui.prompt_float("Target torque (Nm) [optional]", allow_empty=True, min_value=1.0)
    target_torque_rpm = ui.prompt_int("Target torque rpm [optional]", allow_empty=True, min_value=1)
    peak_bmep_kpa = ui.prompt_float("Peak BMEP (kPa) [optional]", allow_empty=True, min_value=1.0)

    rpm_min = ui.prompt_int("RPM min", default=1000, min_value=1)
    rpm_max = ui.prompt_int("RPM max", default=redline, min_value=rpm_min)
    rpm_step = ui.prompt_int("RPM step", default=100, min_value=1)

    ascii_step = ui.prompt_int("ASCII sample step (rpm)", default=500, min_value=1)

    args = SimpleNamespace(
        disp_cc=disp_cc,
        cyl=cyl,
        bore_mm=bore_mm,
        stroke_mm=stroke_mm,
        cycle=cycle,
        idle=idle,
        redline=redline,
        profile=profile,
        fuel=fuel,
        bsfc=bsfc,
        engine_preset=engine_preset,
        target_power_kw=target_power_kw,
        target_power_rpm=target_power_rpm,
        target_torque_nm=target_torque_nm,
        target_torque_rpm=target_torque_rpm,
        peak_bmep_kpa=peak_bmep_kpa,
        rpm_min=rpm_min,
        rpm_max=rpm_max,
        rpm_step=rpm_step,
        save_json=None,
        export_csv=None,
        ascii=True,
        ascii_step=ascii_step,
    )

    run, meta = _compute_match(args)
    if run is None or meta is None:
        return 2

    print("Mode: match")
    print(f"Confidence: {meta.confidence:.2f}")
    if meta.assumptions_made:
        print("Assumptions made:")
        for s in meta.assumptions_made:
            print(" ", s)

    _render_run_sections(run)
    _render_ascii(run, ascii_step)
    _prompt_post_run_io(run, allow_export_curves=True)
    return 0


def _guided_design(defaults: argparse.Namespace | None = None) -> int:
    print("Guided mode: Design")
    target_power_kw = ui.prompt_float("Target power (kW)", default=120.0, min_value=1.0)
    target_power_rpm = ui.prompt_int("Target power rpm [optional]", allow_empty=True, min_value=1)
    redline = ui.prompt_int("Redline rpm", default=7000, min_value=1)
    profile = ui.prompt_choice("VE profile", list_profiles(), default="balanced")
    fuel = ui.prompt_choice("Fuel", ["petrol", "diesel", "e85"], default="petrol")
    bsfc = ui.prompt_float("BSFC g/kWh (blank for auto)", allow_empty=True)

    disp_min_cc = ui.prompt_int("Disp min (cc)", default=1000, min_value=100)
    disp_max_cc = ui.prompt_int("Disp max (cc)", default=6000, min_value=disp_min_cc)
    disp_step_cc = ui.prompt_int("Disp step (cc)", default=250, min_value=1)
    cyls = ui.prompt_float_list("Cylinder options", default=[3, 4, 6, 8])
    cyls_int = [int(round(c)) for c in cyls]
    bmep_max_kpa = ui.prompt_float("Max BMEP (kPa)", default=2000.0, min_value=1.0)
    piston_speed_max = ui.prompt_float("Max piston speed (m/s)", default=20.0, min_value=1.0)
    top_n = ui.prompt_int("Top N candidates", default=5, min_value=1)

    ascii_step = ui.prompt_int("ASCII sample step (rpm)", default=500, min_value=1)

    args = SimpleNamespace(
        target_power_kw=target_power_kw,
        target_power_rpm=target_power_rpm,
        redline=redline,
        profile=profile,
        fuel=fuel,
        bsfc=bsfc,
        disp_min_cc=disp_min_cc,
        disp_max_cc=disp_max_cc,
        disp_step_cc=disp_step_cc,
        cyls=cyls_int,
        bmep_max_kpa=bmep_max_kpa,
        piston_speed_max=piston_speed_max,
        top_n=top_n,
        save_json=None,
        export_candidates_csv=None,
        ascii=True,
        ascii_step=ascii_step,
    )

    from dataclasses import asdict, is_dataclass
    from egstat.solver import design_candidates

    cands = design_candidates(
        target_power_kw=args.target_power_kw,
        target_power_rpm=args.target_power_rpm,
        redline_rpm=args.redline,
        profile=args.profile,
        cycle="4-stroke",
        fuel=args.fuel,
        bsfc_g_per_kwh=args.bsfc,
        bmep_max_kpa=args.bmep_max_kpa,
        piston_speed_max_mps=args.piston_speed_max,
        disp_min_cc=args.disp_min_cc,
        disp_max_cc=args.disp_max_cc,
        disp_step_cc=args.disp_step_cc,
        cylinders_list=args.cyls,
        top_n=args.top_n,
    )

    print("Mode: design")
    if not cands:
        print("No candidates found.")
        return 2

    print(f"Candidates: {len(cands)}")
    best = cands[0]
    print(f"Best score: {best.score:.3f}")

    run = RunData(
        engine=best.engine,
        assumptions=best.assumptions,
        run_config=best.run_config,
        peak_bmep_kpa=best.peak_bmep_kpa,
        vehicle=None,
        drivetrain=None,
        result=best.result,
    )

    _render_run_sections(run)
    _render_ascii(run, ascii_step)

    _prompt_post_run_io(run, allow_export_curves=True)

    if ui.prompt_yes_no("Export candidates CSV?", default=False):
        path = _prompt_save_path("Export candidates CSV path", "candidates.csv", ".csv")
        if path is not None:
            cands_export = [asdict(c) if is_dataclass(c) else c for c in cands]
            export_candidates_csv(path, cands_export)
            print(f"Exported candidates CSV: {path}")

    return 0


def _guided_load() -> int:
    print("Guided mode: Load JSON")
    path = ui.prompt_text("Run JSON path", default="run.json")
    recompute = ui.prompt_yes_no("Recompute from inputs?", default=False)
    ascii_step = ui.prompt_int("ASCII sample step (rpm)", default=500, min_value=1)

    args = SimpleNamespace(
        load_json=path,
        recompute=recompute,
        disp_cc=None,
        cyl=None,
        bore_mm=None,
        stroke_mm=None,
        cycle="4-stroke",
        idle=800,
        redline=7000,
        peak_bmep_kpa=None,
        profile="balanced",
        rpm_min=1000,
        rpm_max=7000,
        rpm_step=100,
        fuel="petrol",
        bsfc=None,
        engine_preset=None,
        vehicle_preset=None,
        gearbox_preset=None,
        mass_kg=None,
        cd=None,
        fa_m2=None,
        crr=None,
        rho=None,
        drivetrain_eff=None,
        final_drive=None,
        tire_radius_m=None,
        gears=None,
        export_csv=None,
        save_json=None,
        ascii=True,
        ascii_step=ascii_step,
    )

    run = _compute_analyze(args)
    if run is None:
        return 2

    _render_run_sections(run)
    _render_vehicle_outputs(run)
    _render_ascii(run, ascii_step)
    _prompt_post_run_io(run, allow_export_curves=True)
    return 0


def _guided_about() -> None:
    ui.print_section("About / Credits")
    print(f"EG-Stat v{APP_VERSION}")
    print("Engine specification & performance calculator.")
    print("v0.2.1 upgraded from v0.2.0,  fixed known bugs.")
    print("Author: Huu Tri (Alvin) Phan")
    print("Contact: alvinphanhuu@gmail.com")
    print("GitHub: https://github.com/k-shii/EG-STAT")


def _guided_menu(default_choice: int | None = None) -> int:
    default_idx = default_choice
    while True:
        print(f"\nEG-Stat guided mode (v{APP_VERSION})")
        choice = ui.prompt_menu(
            [
                "Analyze",
                "Match",
                "Design",
                "Load previous run JSON",
                "About / Credits",
                "Exit",
            ],
            default_index=default_idx,
        )
        default_idx = None
        if choice == 1:
            _guided_analyze()
            if ui.pause("Return to main menu"):
                return 0
            continue
        if choice == 2:
            _guided_match()
            if ui.pause("Return to main menu"):
                return 0
            continue
        if choice == 3:
            _guided_design()
            if ui.pause("Return to main menu"):
                return 0
            continue
        if choice == 4:
            _guided_load()
            if ui.pause("Return to main menu"):
                return 0
            continue
        if choice == 5:
            _guided_about()
            if ui.pause("Return to main menu"):
                return 0
            continue
        return 0


def build_parser(*, require_subcommand: bool = True) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="egstat", description="EG-Stat (core-first) CLI")
    p.add_argument("--version", action="version", version=f"EG-Stat v{APP_VERSION}")
    p.add_argument("-ui", "--ui", action="store_true", help="Launch interactive guided menu")
    sub = p.add_subparsers(dest="cmd")
    sub.required = require_subcommand

    a = sub.add_parser("analyze", help="Analyze a basic engine using templates")
    a.add_argument("--disp-cc", type=float, default=None, help="Displacement in cc (e.g., 1998)")
    a.add_argument("--cyl", type=int, default=None, help="Cylinder count (required if using bore/stroke)")
    a.add_argument("--bore-mm", type=float, default=None, help="Bore in mm")
    a.add_argument("--stroke-mm", type=float, default=None, help="Stroke in mm")
    a.add_argument("--cycle", type=str, default="4-stroke", help="4-stroke or 2-stroke")
    a.add_argument("--idle", type=int, default=800, help="Idle rpm")
    a.add_argument("--redline", type=int, default=7000, help="Redline rpm")
    a.add_argument("--peak-bmep-kpa", type=float, required=False, help="Peak BMEP in kPa (e.g., 1000)")
    a.add_argument("--profile", type=str, default="balanced", choices=list_profiles(), help="Curve profile")
    a.add_argument("--rpm-min", type=int, default=1000)
    a.add_argument("--rpm-max", type=int, default=7000)
    a.add_argument("--rpm-step", type=int, default=100)
    a.add_argument("--fuel", type=str, default="petrol", choices=["petrol", "diesel", "e85"])
    a.add_argument("--bsfc", type=float, default=None, help="Override BSFC (g/kWh)")

    a.add_argument("--mass-kg", type=float, default=None)
    a.add_argument("--cd", type=float, default=None)
    a.add_argument("--fa-m2", type=float, default=None, help="Frontal area (m^2)")
    a.add_argument("--crr", type=float, default=None, help="Rolling resistance coefficient (default ~0.012)")
    a.add_argument("--rho", type=float, default=None, help="Air density kg/m^3 (default 1.225)")
    a.add_argument("--drivetrain-eff", type=float, default=None, help="0-1 (default 0.90)")
    a.add_argument("--final-drive", type=float, default=None)
    a.add_argument("--tire-radius-m", type=float, default=None)
    a.add_argument("--gears", type=float, nargs="+", default=None, help="Gear ratios, e.g. --gears 3.6 2.19 1.41 1.12 0.87 0.69")

    a.add_argument("--engine-preset", type=str, default=None, choices=list_engine_presets())
    a.add_argument("--vehicle-preset", type=str, default=None, choices=list_vehicle_presets())
    a.add_argument("--gearbox-preset", type=str, default=None, choices=list_gearbox_presets())

    a.add_argument("--save-json", type=str, default=None, help="Save inputs + outputs to JSON")
    a.add_argument("--load-json", type=str, default=None, help="Load inputs/outputs from JSON")
    a.add_argument("--export-csv", type=str, default=None, help="Export curves (and speeds if drivetrain known) to CSV")
    a.add_argument("--recompute", action="store_true", help="When loading JSON, recompute result from inputs")
    a.add_argument("--ascii", action="store_true", help="Render ASCII tables/curves")
    a.add_argument("--ascii-step", type=int, default=500, help="RPM step for ASCII sampling")

    m = sub.add_parser("match", help="Match mode: fill missing spec fields from partial inputs + targets")
    m.add_argument("--disp-cc", type=float, default=None, help="Displacement in cc (optional)")
    m.add_argument("--cyl", type=int, default=None, help="Cylinder count (optional)")
    m.add_argument("--bore-mm", type=float, default=None, help="Bore in mm (optional)")
    m.add_argument("--stroke-mm", type=float, default=None, help="Stroke in mm (optional)")
    m.add_argument("--cycle", type=str, default="4-stroke", help="4-stroke or 2-stroke")
    m.add_argument("--idle", type=int, default=800, help="Idle rpm")
    m.add_argument("--redline", type=int, default=7000, help="Redline rpm")
    m.add_argument("--profile", type=str, default="balanced", choices=list_profiles(), help="Curve profile")
    m.add_argument("--fuel", type=str, default="petrol", choices=["petrol", "diesel", "e85"])
    m.add_argument("--bsfc", type=float, default=None, help="Override BSFC (g/kWh)")
    m.add_argument("--engine-preset", type=str, default=None, choices=list_engine_presets())

    m.add_argument("--target-power-kw", type=float, default=None)
    m.add_argument("--target-power-rpm", type=int, default=None)
    m.add_argument("--target-torque-nm", type=float, default=None)
    m.add_argument("--target-torque-rpm", type=int, default=None)

    m.add_argument("--peak-bmep-kpa", type=float, default=None)
    m.add_argument("--rpm-min", type=int, default=1000)
    m.add_argument("--rpm-max", type=int, default=7000)
    m.add_argument("--rpm-step", type=int, default=100)

    m.add_argument("--save-json", type=str, default=None)
    m.add_argument("--export-csv", type=str, default=None)
    m.add_argument("--ascii", action="store_true", help="Render ASCII tables/curves")
    m.add_argument("--ascii-step", type=int, default=500, help="RPM step for ASCII sampling")
    m.set_defaults(func=cmd_match)

    d = sub.add_parser("design", help="Design mode: targets -> candidate specs")
    d.add_argument("--target-power-kw", type=float, required=False)
    d.add_argument("--target-power-rpm", type=int, default=None)
    d.add_argument("--redline", type=int, default=7000)
    d.add_argument("--profile", type=str, default="balanced", choices=list_profiles())
    d.add_argument("--fuel", type=str, default="petrol", choices=["petrol", "diesel", "e85"])
    d.add_argument("--disp-min-cc", type=int, default=1000)
    d.add_argument("--disp-max-cc", type=int, default=6000)
    d.add_argument("--disp-step-cc", type=int, default=250)
    d.add_argument("--cyls", type=int, nargs="+", default=[3, 4, 6, 8])
    d.add_argument("--bmep-max-kpa", type=float, default=2000.0)
    d.add_argument("--piston-speed-max", type=float, default=20.0)
    d.add_argument("--top-n", type=int, default=5)
    d.add_argument("--save-json", type=str, default=None, help="Save best candidate as RunFile JSON")
    d.add_argument("--export-candidates-csv", type=str, default=None, help="Export candidate list CSV")
    d.add_argument("--ascii", action="store_true", help="Render ASCII tables/curves")
    d.add_argument("--ascii-step", type=int, default=500, help="RPM step for ASCII sampling")
    d.set_defaults(func=cmd_design)

    a.set_defaults(func=cmd_analyze)
    return p


def _first_non_flag_arg(argv: list[str]) -> str | None:
    for arg in argv:
        if not arg.startswith("-"):
            return arg
    return None


def _has_help_or_version(argv: list[str]) -> bool:
    return any(arg in ("-h", "--help", "--version") for arg in argv)


def _has_ui_flag(argv: list[str]) -> bool:
    return any(arg in ("-ui", "--ui") for arg in argv)


def _strip_ui_flag(argv: list[str]) -> list[str]:
    return [arg for arg in argv if arg not in ("-ui", "--ui")]


def _should_exit_for_noninteractive_test() -> bool:
    if os.getenv(NONINTERACTIVE_TEST_ENV) == "1":
        print(NONINTERACTIVE_TEST_MARKER)
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        if _should_exit_for_noninteractive_test():
            return 0
        if ui.is_interactive():
            return _guided_menu()
        parser = build_parser(require_subcommand=False)
        parser.print_help()
        return 2

    subcommand = _first_non_flag_arg(argv)
    if subcommand in LEGACY_SUBCOMMANDS:
        parser = build_parser(require_subcommand=True)
        args = parser.parse_args(_strip_ui_flag(argv))

        if args.cmd == "analyze":
            return cmd_analyze(args)
        if args.cmd == "match":
            return cmd_match(args)
        if args.cmd == "design":
            if args.target_power_kw is None:
                print("ERROR: --target-power-kw is required.")
                return 2
            return cmd_design(args)

        parser.print_help()
        return 2

    if _has_help_or_version(argv):
        parser = build_parser(require_subcommand=False)
        parser.parse_args(_strip_ui_flag(argv))
        return 0

    if _has_ui_flag(argv):
        if _should_exit_for_noninteractive_test():
            return 0
        if ui.is_interactive():
            return _guided_menu()
        parser = build_parser(require_subcommand=False)
        parser.print_help()
        return 2

    parser = build_parser(require_subcommand=False)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
