from __future__ import annotations

from egstat.models import EngineSpec, DrivetrainSpec, Result
from egstat.vehicle import speed_kph_from_rpm


def interp_1d(xs: list[float], ys: list[float], x: float) -> float:
    if not xs or len(xs) != len(ys):
        raise ValueError("xs and ys must be same non-zero length")

    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]

    for x0, x1, y0, y1 in zip(xs[:-1], xs[1:], ys[:-1], ys[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    return ys[-1]


def recommend_upshifts(
    result: Result,
    engine: EngineSpec,
    drivetrain: DrivetrainSpec,
) -> list[dict[str, float]]:
    if drivetrain.gears is None or drivetrain.final_drive is None:
        raise ValueError("drivetrain.gears and final_drive required")
    if "rpm" not in result.curves or "torque_nm" not in result.curves:
        raise ValueError("Result must contain curves: rpm, torque_nm")

    gears = drivetrain.gears
    rpms = [float(x) for x in result.curves["rpm"]]
    tq = [float(x) for x in result.curves["torque_nm"]]

    rpm_min = max(engine.idle_rpm, int(min(rpms)))
    rpm_max = min(engine.redline_rpm, int(max(rpms)))

    out: list[dict[str, float]] = []

    # evaluate at curve resolution
    for i in range(len(gears) - 1):
        g1 = gears[i]
        g2 = gears[i + 1]
        ratio_drop = g2 / g1

        # find earliest rpm where wheel torque in next gear >= current
        chosen = None
        for r in rpms:
            if r < rpm_min or r > rpm_max:
                continue

            r_after = r * ratio_drop
            if r_after < rpm_min or r_after > rpm_max:
                continue

            t1 = interp_1d(rpms, tq, r)
            t2 = interp_1d(rpms, tq, r_after)

            wheel_t1 = t1 * g1
            wheel_t2 = t2 * g2

            if wheel_t2 >= wheel_t1:
                chosen = (r, r_after)
                break

        if chosen is None:
            # if never beneficial, shift at redline
            r = float(rpm_max)
            r_after = r * ratio_drop
        else:
            r, r_after = chosen

        row = {
            "from_gear": float(i + 1),
            "to_gear": float(i + 2),
            "upshift_rpm": float(r),
            "post_shift_rpm": float(r_after),
        }

        # Optional: speed at shift if tire radius exists
        if drivetrain.tire_radius_m is not None:
            row["speed_kph_at_shift"] = float(
                speed_kph_from_rpm(r, g1, drivetrain.final_drive, drivetrain.tire_radius_m)
            )

        out.append(row)

    return out
