from egstat.presets import (
    list_engine_presets, list_vehicle_presets, list_gearbox_presets,
    apply_engine_preset, apply_vehicle_preset, apply_gearbox_preset,
)
from egstat.models import Assumptions, VehicleSpec, DrivetrainSpec


def test_lists_contain_expected():
    assert "na_street" in list_engine_presets()
    assert "sedan" in list_vehicle_presets()
    assert "6mt_typical" in list_gearbox_presets()


def test_engine_preset_sets_fields():
    a = Assumptions(ve_profile="balanced", fuel="petrol", bsfc_g_per_kwh=None)
    a2 = apply_engine_preset("diesel_torque", a)
    assert a2.fuel == "diesel"
    assert a2.ve_profile == "torque_biased"


def test_vehicle_preset_fills_values():
    v = VehicleSpec()
    v2 = apply_vehicle_preset("suv", v)
    assert v2.mass_kg is not None and v2.mass_kg > 0
    assert v2.cd is not None and v2.cd > 0
    assert v2.frontal_area_m2 is not None and v2.frontal_area_m2 > 0


def test_gearbox_preset_fills_values():
    g = DrivetrainSpec()
    g2 = apply_gearbox_preset("6mt_typical", g)
    assert g2.gears is not None and len(g2.gears) == 6
    assert g2.final_drive is not None and g2.final_drive > 0
