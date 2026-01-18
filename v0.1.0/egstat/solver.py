from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import List, Optional
from egstat.models import EngineSpec, Assumptions
from dataclasses import dataclass, field
from typing import Optional

from .models import EngineSpec, Assumptions, RunConfig, Result
from .performance import analyze_basic_curves

@dataclass
class MatchResult:
    engine: EngineSpec
    peak_bmep_kpa: float
    confidence: float
    assumptions_made: List[str]


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _cycle_denominator(cycle: str) -> float:
    # Torque-BMEP relationship:
    # 4-stroke: T = (BMEP * Vd) / (4*pi)
    # 2-stroke: T = (BMEP * Vd) / (2*pi)
    c = (cycle or "").lower().strip()
    return 2.0 * pi if "2" in c else 4.0 * pi


def _infer_ratio_from_profile(profile: str) -> float:
    p = (profile or "").lower().strip()
    if "top" in p:
        return 1.10  # oversquare
    if "torque" in p:
        return 0.90  # undersquare
    return 1.00  # square-ish default


def _infer_peak_power_rpm(profile: str, redline: int) -> int:
    p = (profile or "").lower().strip()
    if "top" in p:
        return int(round(0.95 * redline))
    if "torque" in p:
        return int(round(0.80 * redline))
    return int(round(0.88 * redline))


def _infer_peak_torque_rpm(profile: str, redline: int) -> int:
    p = (profile or "").lower().strip()
    if "top" in p:
        return int(round(0.70 * redline))
    if "torque" in p:
        return int(round(0.55 * redline))
    return int(round(0.60 * redline))


def _infer_cylinders_from_disp_l(disp_l: float) -> int:
    # Deterministic, “common sense” buckets
    if disp_l < 1.1:
        return 3
    if disp_l < 2.6:
        return 4
    if disp_l < 3.6:
        return 6
    if disp_l < 5.5:
        return 8
    return 12


def _torque_nm_from_power_kw(power_kw: float, rpm: int) -> float:
    omega = 2.0 * pi * (rpm / 60.0)
    return (power_kw * 1000.0) / omega


def _bmep_kpa_from_torque_nm(torque_nm: float, disp_m3: float, cycle: str) -> float:
    denom = _cycle_denominator(cycle)
    bmep_pa = torque_nm * denom / disp_m3
    return bmep_pa / 1000.0


def _infer_bore_stroke_from_disp(disp_m3: float, cyl: int, bore_to_stroke: float) -> tuple[float, float]:
    # Vcyl = (pi/4) * bore^2 * stroke
    # bore = r * stroke
    # => Vcyl = (pi/4) * r^2 * stroke^3
    v_cyl = disp_m3 / float(cyl)
    r = bore_to_stroke
    stroke_m = (4.0 * v_cyl / (pi * (r ** 2))) ** (1.0 / 3.0)
    bore_m = r * stroke_m
    return bore_m, stroke_m


def match_engine(
    engine: EngineSpec,
    assumptions: Assumptions,
    *,
    target_power_kw: Optional[float] = None,
    target_power_rpm: Optional[int] = None,
    target_torque_nm: Optional[float] = None,
    target_torque_rpm: Optional[int] = None,
    peak_bmep_kpa: Optional[float] = None,
) -> MatchResult:
    """
    Stage 9: Match mode (fill blanks reliably)
    - Fill missing displacement/bore/stroke/cyl via deterministic rules
    - Infer peak_bmep_kpa from target power/torque (or accept explicit override)
    - Return confidence + list of assumptions made
    """
    conf = 1.0
    made: List[str] = []

    # Copy fields out (don’t mutate caller)
    cyl = int(getattr(engine, "cylinders", 0) or 0)
    cycle = getattr(engine, "cycle", None) or "4-stroke"
    bore_m = getattr(engine, "bore_m", None)
    stroke_m = getattr(engine, "stroke_m", None)
    disp_m3 = getattr(engine, "displacement_m3", None)
    idle = int(getattr(engine, "idle_rpm", 800) or 800)
    redline = int(getattr(engine, "redline_rpm", 7000) or 7000)

    profile = getattr(assumptions, "ve_profile", None) or "balanced"

    # ---- Fill missing engine geometry ----
    if disp_m3 is not None and (cyl == 0):
        disp_l = float(disp_m3) * 1000.0
        cyl = _infer_cylinders_from_disp_l(disp_l)
        conf -= 0.15
        made.append(f"Assumed cylinders={cyl} from displacement bucket")

    if (disp_m3 is None) and (bore_m is not None) and (stroke_m is not None) and (cyl != 0):
        disp_m3 = (pi / 4.0) * (bore_m ** 2) * stroke_m * float(cyl)

    if (disp_m3 is not None) and ((bore_m is None) or (stroke_m is None)):
        if cyl == 0:
            # Still nothing to anchor cylinders -> default 4
            cyl = 4
            conf -= 0.20
            made.append("Assumed cylinders=4 (no cylinder count provided)")
        r = _infer_ratio_from_profile(profile)
        bore_m, stroke_m = _infer_bore_stroke_from_disp(float(disp_m3), int(cyl), r)
        conf -= 0.20
        made.append(f"Assumed bore/stroke ratio={r:.2f} from profile '{profile}'")

    if (disp_m3 is None) and (bore_m is None or stroke_m is None):
        # Not enough info to solve geometry deterministically
        conf -= 0.40
        made.append("Missing geometry: provide --disp-cc OR (--cyl + --bore-mm + --stroke-mm)")

    # ---- Infer BMEP ----
    inferred_bmep = peak_bmep_kpa
    if inferred_bmep is None:
        # Prefer torque target (rpm-independent)
        if target_torque_nm is not None and disp_m3 is not None:
            inferred_bmep = _bmep_kpa_from_torque_nm(float(target_torque_nm), float(disp_m3), cycle)
        elif target_power_kw is not None and disp_m3 is not None:
            rp = target_power_rpm
            if rp is None:
                rp = _infer_peak_power_rpm(profile, redline)
                conf -= 0.10
                made.append(f"Assumed peak power rpm={rp} from profile '{profile}'")
            tq = _torque_nm_from_power_kw(float(target_power_kw), int(rp))
            inferred_bmep = _bmep_kpa_from_torque_nm(float(tq), float(disp_m3), cycle)
        else:
            # No targets -> default “street NA-ish”
            inferred_bmep = 1000.0
            conf -= 0.35
            made.append("No target power/torque provided; defaulted peak_bmep_kpa=1000")

    # If user gave a torque rpm but not torque value, it doesn’t help (keep note)
    if target_torque_nm is not None and target_torque_rpm is None:
        rp = _infer_peak_torque_rpm(profile, redline)
        conf -= 0.05
        made.append(f"Assumed peak torque rpm={rp} from profile '{profile}' (informational only)")

    conf = _clamp01(conf)

    # Build final EngineSpec
    out_engine = EngineSpec(
        cylinders=int(cyl) if cyl != 0 else 4,
        cycle=cycle,
        bore_m=bore_m,
        stroke_m=stroke_m,
        displacement_m3=disp_m3,
        idle_rpm=idle,
        redline_rpm=redline,
    )

    return MatchResult(
        engine=out_engine,
        peak_bmep_kpa=float(inferred_bmep),
        confidence=float(conf),
        assumptions_made=made,
    )

@dataclass
class DesignCandidate:
    engine: EngineSpec
    assumptions: Assumptions
    run_config: RunConfig
    peak_bmep_kpa: float
    result: Result
    score: float
    notes: list[str] = field(default_factory=list)


def _interp(xs: list[float], ys: list[float], x: float) -> float:
    # Clamp + linear interpolate
    if not xs:
        return 0.0
    if x <= xs[0]:
        return float(ys[0])
    if x >= xs[-1]:
        return float(ys[-1])
    for i in range(1, len(xs)):
        if x <= xs[i]:
            x0, x1 = xs[i - 1], xs[i]
            y0, y1 = ys[i - 1], ys[i]
            t = (x - x0) / (x1 - x0)
            return float(y0 + t * (y1 - y0))
    return float(ys[-1])


def design_candidates(
    *,
    target_power_kw: float,
    target_power_rpm: Optional[int],
    redline_rpm: int,
    profile: str,
    cycle: str = "4-stroke",
    fuel: str = "petrol",
    bsfc_g_per_kwh: Optional[float] = None,
    bmep_max_kpa: float = 2000.0,
    piston_speed_max_mps: float = 20.0,
    disp_min_cc: int = 1000,
    disp_max_cc: int = 6000,
    disp_step_cc: int = 250,
    cylinders_list: Optional[list[int]] = None,
    top_n: int = 5,
) -> list[DesignCandidate]:
    """
    Deterministic design search:
      - grid search (disp, cyl)
      - compute required peak BMEP by scaling a base run (1000 kPa)
      - filter by constraints
      - score and return top N
    """
    if target_power_kw <= 0:
        return []

    if cylinders_list is None:
        cylinders_list = [3, 4, 6, 8]

    assumptions = Assumptions(ve_profile=profile, fuel=fuel, bsfc_g_per_kwh=bsfc_g_per_kwh)
    cfg = RunConfig(rpm_min=1000, rpm_max=redline_rpm, rpm_step=100)

    out: list[DesignCandidate] = []

    # Grid search
    for disp_cc in range(disp_min_cc, disp_max_cc + 1, disp_step_cc):
        disp_m3 = disp_cc * 1e-6  # cc -> m^3

        for cyl in cylinders_list:
            engine = EngineSpec(
                cylinders=cyl,
                cycle=cycle,
                displacement_m3=disp_m3,
                bore_m=None,
                stroke_m=None,
                idle_rpm=800,
                redline_rpm=redline_rpm,
            )

            notes: list[str] = []
            notes.append(f"Assumed VE profile='{profile}'")
            notes.append("Scaled peak BMEP from a 1000 kPa base run")

            # Base run @ 1000 kPa (linear scaling)
            base = analyze_basic_curves(engine, assumptions, cfg, peak_bmep_kpa=1000.0, profile=profile)
            if not base.curves:
                continue

            rpms = base.curves.get("rpm", [])
            pcurve = base.curves.get("power_kw", [])
            if not rpms or not pcurve:
                continue

            ref_rpm = float(target_power_rpm) if target_power_rpm else float(base.scalars.get("peak_power_rpm", redline_rpm))
            ref_power = _interp([float(r) for r in rpms], [float(p) for p in pcurve], ref_rpm)
            if ref_power <= 0:
                continue

            scale = target_power_kw / ref_power
            peak_bmep = 1000.0 * scale

            # Hard constraints first
            if peak_bmep > bmep_max_kpa:
                continue

            res = analyze_basic_curves(engine, assumptions, cfg, peak_bmep_kpa=peak_bmep, profile=profile)
            if not res.curves:
                continue

            piston_speed = float(res.scalars.get("piston_speed_mps_at_redline", 0.0))
            if piston_speed_max_mps > 0 and piston_speed > piston_speed_max_mps:
                continue

            peak_power = float(res.scalars.get("peak_power_kw", 0.0))
            peak_power_rpm = float(res.scalars.get("peak_power_rpm", 0.0))

            # Score (lower is better)
            # - hit power target
            power_err = abs(peak_power - target_power_kw) / max(target_power_kw, 1e-9)

            # - prefer peak rpm near target rpm if provided
            rpm_err = 0.0
            if target_power_rpm:
                rpm_err = abs(peak_power_rpm - float(target_power_rpm)) / max(float(target_power_rpm), 1.0)

            # - mild penalty for size (prefer smaller engines if equal)
            size_pen = (disp_cc / 1000.0) * 0.02 + (cyl * 0.01)

            score = (power_err * 1.0) + (rpm_err * 0.3) + size_pen

            out.append(
                DesignCandidate(
                    engine=engine,
                    assumptions=assumptions,
                    run_config=cfg,
                    peak_bmep_kpa=peak_bmep,
                    result=res,
                    score=score,
                    notes=notes,
                )
            )

    out.sort(key=lambda c: c.score)
    return out[: max(1, int(top_n))]
