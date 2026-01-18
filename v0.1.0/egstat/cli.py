from __future__ import annotations

import argparse
import sys

from egstat.models import EngineSpec, Assumptions, RunConfig
from egstat.performance import analyze_basic_curves
from egstat.units import mm_to_m, cc_to_m3
from egstat.curves import list_profiles
from egstat.models import VehicleSpec, DrivetrainSpec
from egstat.vehicle import per_gear_redline_speeds_kph, estimate_top_speed
from egstat.shifts import recommend_upshifts
from egstat.presets import (
    list_engine_presets, list_vehicle_presets, list_gearbox_presets,
    apply_engine_preset, apply_vehicle_preset, apply_gearbox_preset,
)
from egstat.io import RunFile, save_run_json, load_run_json, export_curves_csv
from egstat.solver import match_engine


def cmd_analyze(args: argparse.Namespace) -> int:
    loaded = None

    # Available for both normal + load-json paths
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

        # If JSON already contains result and user didn't ask recompute, use it
        if loaded.result is not None and not args.recompute:
            res = loaded.result
        else:
            if peak_bmep_kpa is None:
                print("ERROR: Loaded JSON missing peak_bmep_kpa; cannot recompute.")
                return 2
            res = analyze_basic_curves(engine, assumptions, cfg, peak_bmep_kpa=peak_bmep_kpa)

    else:
        # If not loading, peak_bmep_kpa must be provided
        if args.peak_bmep_kpa is None:
            print("ERROR: --peak-bmep-kpa is required unless --load-json is used.")
            return 2

        if args.disp_cc is None and (args.bore_mm is None or args.stroke_mm is None or args.cyl is None):
            print("ERROR: Provide either --disp-cc OR (--cyl + --bore-mm + --stroke-mm).")
            return 2

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

        # Apply engine preset (overwrites base), then re-apply explicit overrides (explicit wins)
        if args.engine_preset:
            assumptions = apply_engine_preset(args.engine_preset, assumptions)

        # Explicit CLI args should win over preset
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
        return 2

    if not res.curves:
        # likely validation errors stored in issues only
        for s in res.issues:
            print(s)
        if not res.issues:
            print("ERROR: No output produced.")
        return 2

    # Print summary
    disp_l = res.scalars["displacement_l"]
    print(f"Displacement: {disp_l:.3f} L")
    print(f"Profile: {assumptions.ve_profile}")
    print(f"Peak BMEP: {float(peak_bmep_kpa):.1f} kPa")
    print(f"Peak torque: {res.scalars['peak_torque_nm']:.1f} Nm @ {int(res.scalars['peak_torque_rpm'])} rpm")
    print(f"Peak power:  {res.scalars['peak_power_kw']:.1f} kW @ {int(res.scalars['peak_power_rpm'])} rpm")
    print(f"Fuel: {assumptions.fuel}")
    print(f"BSFC: {res.scalars['bsfc_g_per_kwh']:.0f} g/kWh")
    print(f"Fuel @ peak power (WOT): {res.scalars['fuel_wot_lph_at_peak_power']:.1f} L/h")
    print(f"Fuel @ 20 kW cruise est: {res.scalars['fuel_cruise_lph_at_20kw']:.1f} L/h")

    if "piston_speed_mps_at_redline" in res.scalars:
        print(f"Piston speed @ redline: {res.scalars['piston_speed_mps_at_redline']:.2f} m/s")

    if res.issues:
        print("\nWarnings:")
        for s in res.issues:
            print(" ", s)

    # Stage 6 (optional): vehicle + gearing outputs
    have_vehicle = (veh is not None) or (args.vehicle_preset is not None) or (args.mass_kg is not None and args.cd is not None and args.fa_m2 is not None)
    have_drive = (drv is not None) or (args.gearbox_preset is not None) or (args.gears is not None and args.final_drive is not None and args.tire_radius_m is not None)

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

        # Apply presets if chosen (preset fills blanks), then explicit args override preset
        if args.vehicle_preset:
            veh = apply_vehicle_preset(args.vehicle_preset, veh)
        if args.gearbox_preset:
            drv = apply_gearbox_preset(args.gearbox_preset, drv)

        # Explicit args override preset (only if provided)
        if args.mass_kg is not None: veh.mass_kg = args.mass_kg
        if args.cd is not None: veh.cd = args.cd
        if args.fa_m2 is not None: veh.frontal_area_m2 = args.fa_m2
        if args.crr is not None: veh.crr = args.crr
        if args.rho is not None: veh.air_density_kg_m3 = args.rho

        if args.gears is not None: drv.gears = args.gears
        if args.final_drive is not None: drv.final_drive = args.final_drive
        if args.tire_radius_m is not None: drv.tire_radius_m = args.tire_radius_m
        if args.drivetrain_eff is not None: drv.drivetrain_efficiency = args.drivetrain_eff

        speeds = per_gear_redline_speeds_kph(engine, drv)
        print("\nGear speeds @ redline:")
        for i, skph in enumerate(speeds, start=1):
            print(f"  Gear {i}: {skph:.1f} km/h")

        ts = estimate_top_speed(res, engine, veh, drv)
        print(f"\nTop speed est: {ts['top_speed_kph']:.1f} km/h  (gear {int(ts['top_speed_gear'])} @ {int(ts['top_speed_rpm'])} rpm)")
        print(f"Assumptions: crr={ts['crr']:.4f}, rho={ts['rho']:.3f}, drivetrain_eff={ts['drivetrain_eff']:.2f}")

        ups = recommend_upshifts(res, engine, drv)
        print("\nUpshift suggestions:")
        for u in ups:
            if "speed_kph_at_shift" in u:
                print(f"  {int(u['from_gear'])}->{int(u['to_gear'])}: {int(u['upshift_rpm'])} rpm (drops to {int(u['post_shift_rpm'])}) @ {u['speed_kph_at_shift']:.1f} km/h")
            else:
                print(f"  {int(u['from_gear'])}->{int(u['to_gear'])}: {int(u['upshift_rpm'])} rpm (drops to {int(u['post_shift_rpm'])})")

    # Export CSV if requested
    if args.export_csv:
        export_curves_csv(args.export_csv, res, drv)
        print(f"\nExported CSV: {args.export_csv}")

    # Save JSON if requested
    if args.save_json:
        run = RunFile(
            version="0.0.1",
            engine=engine,
            assumptions=assumptions,
            run_config=cfg,
            peak_bmep_kpa=peak_bmep_kpa,
            vehicle=veh,
            drivetrain=drv,
            result=res,
        )
        save_run_json(args.save_json, run)
        print(f"Saved JSON: {args.save_json}")

    return 0

def cmd_match(args: argparse.Namespace) -> int:
    # Stage 9: Match mode (fill blanks reliably)
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

    # Apply engine preset (overwrites base), then re-apply explicit overrides (explicit wins)
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
        return 2

    if not res.curves:
        for s in res.issues:
            print(s)
        if not res.issues:
            print("ERROR: No output produced.")
        return 2

    print("Mode: match")
    print(f"Confidence: {m.confidence:.2f}")
    if m.assumptions_made:
        print("Assumptions made:")
        for s in m.assumptions_made:
            print(" ", s)

    # Print summary (same style as analyze)
    disp_l = res.scalars["displacement_l"]
    print(f"\nDisplacement: {disp_l:.3f} L")
    print(f"Profile: {args.profile}")
    print(f"Peak BMEP: {m.peak_bmep_kpa:.1f} kPa")
    print(f"Peak torque: {res.scalars['peak_torque_nm']:.1f} Nm @ {int(res.scalars['peak_torque_rpm'])} rpm")
    print(f"Peak power:  {res.scalars['peak_power_kw']:.1f} kW @ {int(res.scalars['peak_power_rpm'])} rpm")
    print(f"Fuel: {args.fuel}")
    print(f"BSFC: {res.scalars['bsfc_g_per_kwh']:.0f} g/kWh")
    print(f"Fuel @ peak power (WOT): {res.scalars['fuel_wot_lph_at_peak_power']:.1f} L/h")
    print(f"Fuel @ 20 kW cruise est: {res.scalars['fuel_cruise_lph_at_20kw']:.1f} L/h")

    if "piston_speed_mps_at_redline" in res.scalars:
        print(f"Piston speed @ redline: {res.scalars['piston_speed_mps_at_redline']:.2f} m/s")

    if res.issues:
        print("\nWarnings:")
        for s in res.issues:
            print(" ", s)

    # Export/save (same behavior)
    if args.export_csv:
        export_curves_csv(args.export_csv, res, None)
        print(f"\nExported CSV: {args.export_csv}")

    if args.save_json:
        run = RunFile(
            version="0.0.1",
            engine=m.engine,
            assumptions=assumptions,
            run_config=cfg,
            peak_bmep_kpa=m.peak_bmep_kpa,
            vehicle=None,
            drivetrain=None,
            result=res,
        )
        save_run_json(args.save_json, run)
        print(f"Saved JSON: {args.save_json}")

    return 0

def cmd_design(args: argparse.Namespace) -> int:
    # Stage 9: Design mode (constraint-based search)
    # Goal: targets -> candidate specs with feasibility scoring.

    from dataclasses import asdict, is_dataclass
    from egstat.solver import design_candidates  # keep import here to avoid circulars
    from egstat.io import RunFile, save_run_json, export_candidates_csv

    # Call solver with keyword args (design_candidates is kw-only)
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

    # Solver returns DesignCandidate dataclasses
    best = cands[0]
    print(f"Best score: {best.score:.3f}")

    res = best.result
    disp_l = res.scalars.get("displacement_l", None)
    if disp_l is not None:
        print(f"Displacement: {disp_l:.3f} L")

    s = res.scalars
    print(f"Peak torque: {s['peak_torque_nm']:.1f} Nm @ {int(s['peak_torque_rpm'])} rpm")
    print(f"Peak power:  {s['peak_power_kw']:.1f} kW @ {int(s['peak_power_rpm'])} rpm")

    # Export candidates CSV (convert dataclasses -> dicts if needed)
    if getattr(args, "export_candidates_csv", None):
        cands_export = [asdict(c) if is_dataclass(c) else c for c in cands]
        export_candidates_csv(args.export_candidates_csv, cands_export)
        print(f"Exported candidates CSV: {args.export_candidates_csv}")

    # Save best candidate as RunFile JSON
    if getattr(args, "save_json", None):
        run = RunFile(
            version="0.0.1",
            engine=best.engine,
            assumptions=best.assumptions,
            run_config=best.run_config,
            peak_bmep_kpa=best.peak_bmep_kpa,
            vehicle=None,
            drivetrain=None,
            result=best.result,
        )
        save_run_json(args.save_json, run)
        print(f"Saved JSON: {args.save_json}")

    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="egstat", description="EG-Stat (core-first) CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

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

    # Vehicle + drivetrain (Stage 6)
    a.add_argument("--mass-kg", type=float, default=None)
    a.add_argument("--cd", type=float, default=None)
    a.add_argument("--fa-m2", type=float, default=None, help="Frontal area (m^2)")
    a.add_argument("--crr", type=float, default=None, help="Rolling resistance coefficient (default ~0.012)")
    a.add_argument("--rho", type=float, default=None, help="Air density kg/m^3 (default 1.225)")
    a.add_argument("--drivetrain-eff", type=float, default=None, help="0-1 (default 0.90)")
    a.add_argument("--final-drive", type=float, default=None)
    a.add_argument("--tire-radius-m", type=float, default=None)
    a.add_argument("--gears", type=float, nargs="+", default=None, help="Gear ratios, e.g. --gears 3.6 2.19 1.41 1.12 0.87 0.69")

    # Stage 7 Preset
    a.add_argument("--engine-preset", type=str, default=None, choices=list_engine_presets())
    a.add_argument("--vehicle-preset", type=str, default=None, choices=list_vehicle_presets())
    a.add_argument("--gearbox-preset", type=str, default=None, choices=list_gearbox_presets())

    # Stage 8 Export
    a.add_argument("--save-json", type=str, default=None, help="Save inputs + outputs to JSON")
    a.add_argument("--load-json", type=str, default=None, help="Load inputs/outputs from JSON")
    a.add_argument("--export-csv", type=str, default=None, help="Export curves (and speeds if drivetrain known) to CSV")
    a.add_argument("--recompute", action="store_true", help="When loading JSON, recompute result from inputs")
    
    # Stage 9 + 10
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

    # Targets
    m.add_argument("--target-power-kw", type=float, default=None)
    m.add_argument("--target-power-rpm", type=int, default=None)
    m.add_argument("--target-torque-nm", type=float, default=None)
    m.add_argument("--target-torque-rpm", type=int, default=None)

    # Optional override (otherwise inferred)
    m.add_argument("--peak-bmep-kpa", type=float, default=None)
    m.add_argument("--rpm-min", type=int, default=1000)
    m.add_argument("--rpm-max", type=int, default=7000)
    m.add_argument("--rpm-step", type=int, default=100)

    # IO
    m.add_argument("--save-json", type=str, default=None)
    m.add_argument("--export-csv", type=str, default=None)
    m.set_defaults(func=cmd_match)

    # Design
    d = sub.add_parser("design", help="Design mode: targets -> candidate specs")
    d.add_argument("--target-power-kw", type=float, required=True)
    d.add_argument("--target-power-rpm", type=int, default=None)
    d.add_argument("--redline", type=int, default=7000)
    d.add_argument("--profile", type=str, default="balanced", choices=list_profiles())
    d.add_argument("--fuel", type=str, default="petrol", choices=["petrol", "diesel", "e85"])  # PATCH: allow --fuel in design
    d.add_argument("--disp-min-cc", type=int, default=1000)
    d.add_argument("--disp-max-cc", type=int, default=6000)
    d.add_argument("--disp-step-cc", type=int, default=250)
    d.add_argument("--cyls", type=int, nargs="+", default=[3, 4, 6, 8])
    d.add_argument("--bmep-max-kpa", type=float, default=2000.0)
    d.add_argument("--piston-speed-max", type=float, default=20.0)
    d.add_argument("--top-n", type=int, default=5)
    d.add_argument("--save-json", type=str, default=None, help="Save best candidate as RunFile JSON")
    d.add_argument("--export-candidates-csv", type=str, default=None, help="Export candidate list CSV")
    d.set_defaults(func=cmd_design)
    a.set_defaults(func=cmd_analyze)
    return p

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
