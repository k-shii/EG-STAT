from __future__ import annotations

import sys
from typing import Iterable, Sequence

BAR_WIDTH = 60


def is_interactive() -> bool:
    return sys.stdin.isatty()


def pause(message: str = "Press Enter to return to menu", *, allow_quit: bool = True) -> bool:
    if not is_interactive():
        return False
    suffix = " (Enter to continue"
    if allow_quit:
        suffix += ", q to quit)"
    else:
        suffix += ")"
    raw = input(f"{message}{suffix}: ").strip().lower()
    return allow_quit and raw in ("q", "quit", "exit")


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def print_kv(label: str, value: str) -> None:
    print(f"  {label}: {value}")


def format_optional(value: float | int | None, fmt: str = "{:.1f}", none_label: str = "auto") -> str:
    if value is None:
        return none_label
    try:
        return fmt.format(value)
    except Exception:
        return str(value)


def prompt_yes_no(label: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{label} [{suffix}]: ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Please enter y or n.")


def prompt_text(label: str, default: str | None = None, allow_empty: bool = False) -> str | None:
    while True:
        suffix = f" (default {default})" if default else ""
        raw = input(f"{label}{suffix}: ").strip()
        if raw == "":
            if default is not None:
                return default
            if allow_empty:
                return None
            print("Value required.")
            continue
        return raw


def prompt_int(
    label: str,
    default: int | None = None,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
    allow_empty: bool = False,
) -> int | None:
    while True:
        suffix = f" (default {default})" if default is not None else (" (blank for auto)" if allow_empty else "")
        raw = input(f"{label}{suffix}: ").strip()
        if raw == "":
            if default is not None:
                return default
            if allow_empty:
                return None
            print("Value required.")
            continue
        try:
            value = int(raw)
        except ValueError:
            print("Invalid integer.")
            continue
        if min_value is not None and value < min_value:
            print(f"Must be >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Must be <= {max_value}.")
            continue
        return value


def prompt_float(
    label: str,
    default: float | None = None,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    allow_empty: bool = False,
) -> float | None:
    while True:
        suffix = f" (default {default})" if default is not None else (" (blank for auto)" if allow_empty else "")
        raw = input(f"{label}{suffix}: ").strip()
        if raw == "":
            if default is not None:
                return default
            if allow_empty:
                return None
            print("Value required.")
            continue
        if allow_empty and raw.lower() in ("auto", "none"):
            return None
        try:
            value = float(raw)
        except ValueError:
            print("Invalid number.")
            continue
        if min_value is not None and value < min_value:
            print(f"Must be >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Must be <= {max_value}.")
            continue
        return value


def prompt_choice(label: str, choices: Sequence[str], default: str | None = None) -> str:
    print(f"{label}:")
    for i, choice in enumerate(choices, start=1):
        print(f"  [{i}] {choice}")
    default_idx = None
    if default in choices:
        default_idx = choices.index(default) + 1
    while True:
        prompt = f"Select [1-{len(choices)}]"
        if default_idx is not None:
            prompt += f" (default {default_idx})"
        raw = input(f"{prompt}: ").strip()
        if raw == "" and default_idx is not None:
            return choices[default_idx - 1]
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return choices[idx - 1]
        for choice in choices:
            if raw.lower() == choice.lower():
                return choice
        print("Invalid selection.")


def prompt_menu(options: Sequence[str], default_index: int | None = None) -> int:
    for i, opt in enumerate(options, start=1):
        print(f"[{i}] {opt}")
    while True:
        prompt = f"Select [1-{len(options)}]"
        if default_index is not None:
            prompt += f" (default {default_index})"
        raw = input(f"{prompt}: ").strip().lower()
        if raw == "" and default_index is not None:
            return default_index
        if raw in ("q", "quit", "exit"):
            return len(options)
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return idx
        print("Invalid selection.")


def prompt_preset(
    label: str,
    presets: Sequence[tuple[str, str]],
    *,
    default: str | None = None,
    allow_none: bool = True,
) -> str | None:
    print(f"{label}:")
    offset = 1
    if allow_none:
        print("  [0] None")
        offset = 1
    for i, (name, desc) in enumerate(presets, start=1):
        print(f"  [{i}] {name} - {desc}")
    default_idx = None
    if default is not None:
        for i, (name, _) in enumerate(presets, start=1):
            if name == default:
                default_idx = i
                break
    while True:
        prompt = f"Select [0-{len(presets)}]" if allow_none else f"Select [1-{len(presets)}]"
        if default_idx is not None:
            prompt += f" (default {default_idx})"
        raw = input(f"{prompt}: ").strip()
        if raw == "" and default_idx is not None:
            return presets[default_idx - 1][0]
        if raw.isdigit():
            idx = int(raw)
            if allow_none and idx == 0:
                return None
            if 1 <= idx <= len(presets):
                return presets[idx - 1][0]
        for name, _ in presets:
            if raw.lower() == name.lower():
                return name
        print("Invalid selection.")


def prompt_float_list(label: str, default: list[float] | None = None) -> list[float]:
    default_str = None
    if default:
        default_str = " ".join(f"{v:g}" for v in default)
    while True:
        suffix = f" (default {default_str})" if default_str else ""
        raw = input(f"{label}{suffix}: ").strip()
        if raw == "":
            if default is not None:
                return list(default)
            print("Value required.")
            continue
        parts = [p for p in raw.replace(",", " ").split(" ") if p]
        try:
            values = [float(p) for p in parts]
        except ValueError:
            print("Invalid list. Use space or comma separated numbers.")
            continue
        if not values:
            print("Provide at least one number.")
            continue
        if any(v <= 0 for v in values):
            print("Values must be > 0.")
            continue
        return values


def _sample_indices(rpms: Iterable[float], step_rpm: int) -> list[int]:
    rpms_list = [float(r) for r in rpms]
    if not rpms_list:
        return []
    step = max(1.0, float(step_rpm))
    indices: list[int] = []
    next_rpm = rpms_list[0]
    for i, rpm in enumerate(rpms_list):
        if rpm + 1e-9 >= next_rpm:
            indices.append(i)
            next_rpm += step
    if indices and indices[-1] != len(rpms_list) - 1:
        indices.append(len(rpms_list) - 1)
    return indices


def render_ascii_table(curves: dict[str, list[float]], step_rpm: int) -> None:
    rpms = curves.get("rpm", [])
    tq = curves.get("torque_nm", [])
    pw = curves.get("power_kw", [])
    bmep = curves.get("bmep_kpa", [])
    n = min(len(rpms), len(tq), len(pw), len(bmep))
    if n == 0:
        return
    indices = _sample_indices(rpms[:n], step_rpm)
    rows = []
    for i in indices:
        rows.append((
            f"{int(round(rpms[i]))}",
            f"{float(tq[i]):.1f}",
            f"{float(pw[i]):.1f}",
            f"{float(bmep[i]):.1f}",
        ))
    headers = ("rpm", "torque_nm", "power_kw", "bmep_kpa")
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    print(f"Sampled every ~{step_rpm} rpm")
    header_line = "  ".join(h.rjust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(row[i].rjust(widths[i]) for i in range(len(headers))))


def _render_curve_block(
    title: str,
    unit: str,
    rpms: list[float],
    values: list[float],
    step_rpm: int,
    width: int = BAR_WIDTH,
) -> None:
    if not rpms or not values:
        return
    n = min(len(rpms), len(values))
    rpms = [float(r) for r in rpms[:n]]
    values = [float(v) for v in values[:n]]
    indices = _sample_indices(rpms, step_rpm)
    vmax = max(values) if values else 1.0
    if vmax <= 0:
        vmax = 1.0
    print(f"{title} (auto-scaled to {vmax:.1f} {unit})")
    for i in indices:
        rpm = int(round(rpms[i]))
        val = values[i]
        bar_len = int(round((val / vmax) * width))
        if bar_len < 0:
            bar_len = 0
        if bar_len > width:
            bar_len = width
        bar = "#" * bar_len
        print(f"{rpm:>5} |{bar:<{width}}| {val:.1f} {unit}")


def render_ascii_curves(curves: dict[str, list[float]], step_rpm: int) -> None:
    rpms = curves.get("rpm", [])
    tq = curves.get("torque_nm", [])
    pw = curves.get("power_kw", [])
    if not rpms:
        return
    _render_curve_block("Torque vs RPM", "Nm", rpms, tq, step_rpm, BAR_WIDTH)
    print("")
    _render_curve_block("Power vs RPM", "kW", rpms, pw, step_rpm, BAR_WIDTH)
