from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ValidationIssue:
    level: str  # "ERROR" or "WARN"
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.field}: {self.message}"


def _is_pos(x: float | int | None) -> bool:
    return x is not None and x > 0


def validate_engine_inputs(
    *,
    cylinders: int | None,
    bore_m: float | None,
    stroke_m: float | None,
    displacement_m3: float | None,
    idle_rpm: int | None,
    redline_rpm: int | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if cylinders is None:
        issues.append(ValidationIssue("ERROR", "cylinders", "Missing cylinder count."))
    elif cylinders <= 0:
        issues.append(ValidationIssue("ERROR", "cylinders", "Must be > 0."))

    if bore_m is not None and bore_m <= 0:
        issues.append(ValidationIssue("ERROR", "bore_m", "Must be > 0."))

    if stroke_m is not None and stroke_m <= 0:
        issues.append(ValidationIssue("ERROR", "stroke_m", "Must be > 0."))

    if displacement_m3 is not None and displacement_m3 <= 0:
        issues.append(ValidationIssue("ERROR", "displacement_m3", "Must be > 0."))

    if idle_rpm is not None and idle_rpm <= 0:
        issues.append(ValidationIssue("ERROR", "idle_rpm", "Must be > 0."))

    if redline_rpm is not None and redline_rpm <= 0:
        issues.append(ValidationIssue("ERROR", "redline_rpm", "Must be > 0."))

    if _is_pos(idle_rpm) and _is_pos(redline_rpm):
        if redline_rpm <= idle_rpm:
            issues.append(
                ValidationIssue("ERROR", "redline_rpm", "Must be greater than idle_rpm.")
            )
        elif redline_rpm < idle_rpm + 500:
            issues.append(
                ValidationIssue("WARN", "redline_rpm", "Very low gap between idle and redline.")
            )

    # "Missing core geometry" warning (allowed, not fatal for now)
    if displacement_m3 is None and (bore_m is None or stroke_m is None):
        issues.append(
            ValidationIssue(
                "WARN",
                "displacement",
                "Provide displacement_m3 or (bore_m + stroke_m) for full calculations.",
            )
        )

    return issues


def has_errors(issues: Iterable[ValidationIssue]) -> bool:
    return any(i.level == "ERROR" for i in issues)
