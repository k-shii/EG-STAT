from egstat.models import EngineSpec
from egstat.validate import validate_engine_inputs, has_errors


def test_engine_spec_to_from_dict():
    e = EngineSpec(cylinders=4, bore_m=0.086, stroke_m=0.086, redline_rpm=7000)
    d = e.to_dict()
    e2 = EngineSpec.from_dict(d)
    assert e2.cylinders == 4
    assert e2.bore_m == 0.086
    assert e2.stroke_m == 0.086
    assert e2.redline_rpm == 7000


def test_validation_catches_bad_values():
    issues = validate_engine_inputs(
        cylinders=0,
        bore_m=-0.1,
        stroke_m=0.0,
        displacement_m3=-1.0,
        idle_rpm=800,
        redline_rpm=700,
    )
    assert has_errors(issues)
