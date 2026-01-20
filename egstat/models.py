from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any
from dataclasses import fields

def _from_dict(cls, data):
    if data is None:
        return None
    allowed = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in allowed}
    return cls(**kwargs)



@dataclass
class EngineSpec:
    cylinders: int
    cycle: str = "4-stroke"  # later: use an enum
    bore_m: float | None = None
    stroke_m: float | None = None
    displacement_m3: float | None = None
    idle_rpm: int = 800
    redline_rpm: int = 6500

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "EngineSpec":
        return _from_dict(EngineSpec, data)


@dataclass
class VehicleSpec:
    mass_kg: float | None = None
    cd: float | None = None
    frontal_area_m2: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VehicleSpec":
        return _from_dict(VehicleSpec, data)


@dataclass
class DrivetrainSpec:
    gears: list[float] | None = None
    final_drive: float | None = None
    tire_radius_m: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DrivetrainSpec":
        return _from_dict(DrivetrainSpec, data)


@dataclass
class Assumptions:
    ve_profile: str = "balanced"
    friction_class: str = "oem"
    fuel: str = "petrol"  # petrol/diesel/e85 (basic for now)
    bsfc_g_per_kwh: float | None = None  # if None, use fuel preset

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Assumptions":
        return _from_dict(Assumptions, data)


@dataclass
class RunConfig:
    rpm_min: int = 1000
    rpm_max: int = 7000
    rpm_step: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RunConfig":
        return _from_dict(RunConfig, data)


@dataclass
class Result:
    scalars: dict[str, float] = field(default_factory=dict)
    curves: dict[str, list[float]] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Result":
        return _from_dict(Result, data)

@dataclass
class VehicleSpec:
    mass_kg: float | None = None
    cd: float | None = None
    frontal_area_m2: float | None = None
    crr: float | None = None
    air_density_kg_m3: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VehicleSpec":
        return _from_dict(VehicleSpec, data)

@dataclass
class DrivetrainSpec:
    gears: list[float] | None = None
    final_drive: float | None = None
    tire_radius_m: float | None = None
    drivetrain_efficiency: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DrivetrainSpec":
        return _from_dict(DrivetrainSpec, data)
