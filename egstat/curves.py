from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurveTemplate:
    name: str
    points: list[tuple[float, float]]  # (x in [0..1], y in [0..1])


TEMPLATES: dict[str, CurveTemplate] = {
    # Earlier torque peak, falls off earlier
    "torque_biased": CurveTemplate(
        name="torque_biased",
        points=[
            (0.00, 0.35),
            (0.15, 0.65),
            (0.35, 0.95),
            (0.45, 1.00),  # peak earlier
            (0.60, 0.92),
            (0.75, 0.78),
            (0.90, 0.62),
            (1.00, 0.50),
        ],
    ),
    # Middle-ish peak
    "balanced": CurveTemplate(
        name="balanced",
        points=[
            (0.00, 0.30),
            (0.15, 0.62),
            (0.35, 0.90),
            (0.55, 1.00),  # peak mid
            (0.70, 0.95),
            (0.85, 0.82),
            (1.00, 0.70),
        ],
    ),
    # Later peak, better top end
    "top_end": CurveTemplate(
        name="top_end",
        points=[
            (0.00, 0.20),
            (0.20, 0.55),
            (0.40, 0.80),
            (0.60, 0.95),
            (0.72, 1.00),  # peak later
            (0.85, 0.98),
            (1.00, 0.92),
        ],
    ),
}


def list_profiles() -> list[str]:
    return sorted(TEMPLATES.keys())


def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def piecewise_linear(points: list[tuple[float, float]], x: float) -> float:
    """
    Linear interpolation on sorted points. Clamps outside [0..1].
    """
    x = _clamp(x, 0.0, 1.0)
    pts = sorted(points, key=lambda p: p[0])

    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]

    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    # Should not happen
    return pts[-1][1]


def normalized_profile(profile: str, x: float) -> float:
    """
    Returns y in [0..1] representing normalized "bmep factor" at rpm fraction x.
    """
    if profile not in TEMPLATES:
        raise ValueError(f"Unknown profile '{profile}'. Valid: {list_profiles()}")
    y = piecewise_linear(TEMPLATES[profile].points, x)
    return _clamp(y, 0.0, 1.0)


def rpm_fraction(rpm: float, rpm_min: float, rpm_max: float) -> float:
    if rpm_max <= rpm_min:
        raise ValueError("rpm_max must be > rpm_min")
    return _clamp((rpm - rpm_min) / (rpm_max - rpm_min), 0.0, 1.0)
