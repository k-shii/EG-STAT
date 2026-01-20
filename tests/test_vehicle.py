from egstat.vehicle import speed_kph_from_rpm, road_load_power_w
from egstat.models import EngineSpec, VehicleSpec, DrivetrainSpec, Result
from egstat.vehicle import estimate_top_speed


def test_speed_mapping_simple():
    # rpm=60, gear=1, final=1, r=0.3 -> 1 rev/s -> v = circumference = 2*pi*0.3 m/s
    v = speed_kph_from_rpm(60.0, 1.0, 1.0, 0.3)
    assert 6.7 <= v <= 6.9


def test_road_load_positive():
    p = road_load_power_w(30.0, mass_kg=1500, cd=0.3, frontal_area_m2=2.2)
    assert p > 0


def test_top_speed_increases_with_power():
    engine = EngineSpec(cylinders=4, displacement_m3=0.002, idle_rpm=800, redline_rpm=7000)
    veh = VehicleSpec(mass_kg=1500, cd=0.30, frontal_area_m2=2.2)
    drv = DrivetrainSpec(gears=[1.0], final_drive=3.0, tire_radius_m=0.30, drivetrain_efficiency=0.90)

    rpms = [1000.0, 3000.0, 5000.0, 7000.0]

    res_hi = Result(curves={"rpm": rpms, "power_kw": [100.0, 100.0, 100.0, 100.0]})
    res_lo = Result(curves={"rpm": rpms, "power_kw": [50.0, 50.0, 50.0, 50.0]})

    ts_hi = estimate_top_speed(res_hi, engine, veh, drv)["top_speed_kph"]
    ts_lo = estimate_top_speed(res_lo, engine, veh, drv)["top_speed_kph"]

    assert ts_hi > ts_lo
