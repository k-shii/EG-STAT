from egstat.models import EngineSpec, DrivetrainSpec, Result
from egstat.shifts import recommend_upshifts


def test_upshift_defaults_to_redline_when_flat_torque():
    engine = EngineSpec(cylinders=4, displacement_m3=0.002, idle_rpm=800, redline_rpm=7000)
    drv = DrivetrainSpec(gears=[3.0, 2.0], final_drive=4.0, tire_radius_m=0.30)

    rpms = [1000.0, 3000.0, 5000.0, 7000.0]
    torque = [200.0, 200.0, 200.0, 200.0]  # flat torque, lower gear always better -> shift at redline

    res = Result(curves={"rpm": rpms, "torque_nm": torque})
    ups = recommend_upshifts(res, engine, drv)

    assert len(ups) == 1
    assert int(ups[0]["upshift_rpm"]) == 7000
