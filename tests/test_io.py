from egstat.models import EngineSpec, Assumptions, RunConfig, VehicleSpec, DrivetrainSpec
from egstat.performance import analyze_basic_curves
from egstat.io import RunFile, save_run_json, load_run_json, export_curves_csv


def test_json_roundtrip(tmp_path):
    engine = EngineSpec(cylinders=4, displacement_m3=0.001998, idle_rpm=800, redline_rpm=7000)
    assumptions = Assumptions(ve_profile="balanced", fuel="petrol", bsfc_g_per_kwh=None)
    cfg = RunConfig(rpm_min=1000, rpm_max=7000, rpm_step=100)
    res = analyze_basic_curves(engine, assumptions, cfg, peak_bmep_kpa=1000)

    veh = VehicleSpec(mass_kg=1500, cd=0.29, frontal_area_m2=2.2)
    drv = DrivetrainSpec(gears=[3.6, 2.19, 1.41, 1.12, 0.87, 0.69], final_drive=4.1, tire_radius_m=0.31)

    run = RunFile(
        version="0.0.1",
        engine=engine,
        assumptions=assumptions,
        run_config=cfg,
        peak_bmep_kpa=1000,
        vehicle=veh,
        drivetrain=drv,
        result=res,
    )

    path = tmp_path / "run.json"
    save_run_json(path, run)

    loaded = load_run_json(path)
    assert loaded.engine.redline_rpm == 7000
    assert loaded.assumptions.fuel == "petrol"
    assert loaded.peak_bmep_kpa == 1000
    assert loaded.result is not None
    assert "peak_power_kw" in loaded.result.scalars


def test_export_csv(tmp_path):
    engine = EngineSpec(cylinders=4, displacement_m3=0.001998, idle_rpm=800, redline_rpm=7000)
    assumptions = Assumptions(ve_profile="balanced", fuel="petrol", bsfc_g_per_kwh=None)
    cfg = RunConfig(rpm_min=1000, rpm_max=7000, rpm_step=100)
    res = analyze_basic_curves(engine, assumptions, cfg, peak_bmep_kpa=1000)

    drv = DrivetrainSpec(gears=[3.6, 2.19], final_drive=4.1, tire_radius_m=0.31)

    out = tmp_path / "out.csv"
    export_curves_csv(out, res, drv)

    text = out.read_text(encoding="utf-8").splitlines()
    assert text[0].startswith("rpm,bmep_kpa,torque_nm,power_kw,speed_kph_g1")
    assert len(text) > 5
