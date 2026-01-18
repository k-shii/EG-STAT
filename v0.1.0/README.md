# EG-Stat — Engine Geometry & Statistics

**Version 0.1.0**
**18/1/2026**

EG-Stat is a **Python-based engine specification and performance calculator** built with a clean, modular, engineering-first architecture.

This release presents EG-Stat as a usable public tool: a command-line application capable of generating engine performance curves, solving incomplete specifications, and exploring feasible engine designs under real engineering constraints.

**Author:** Huu Tri (Alvin) Phan
**GitHub:** K-shii
**License:** MIT

---

## What EG-Stat does (v0.1.0)

EG-Stat provides three complete workflows:

* **Analyze** — Generate torque and power curves from an engine specification
* **Match** — Infer missing engine parameters from partial specs and performance targets, with confidence scoring and explicit assumptions
* **Design** — Explore and rank candidate engine configurations based on targets and constraints

All calculations are **ICE-first**, use **SI units internally**, and prioritise transparency over black-box optimisation.

---

## Key features

* Torque & power curve generation across RPM
* Peak power, torque, and BMEP reporting
* Fuel consumption estimates (WOT and cruise)
* Constraint-based engine design exploration
* JSON save/load for reproducible runs
* CSV export for curves and candidate results
* Automated test coverage (pytest)

---

## Supported fuels (v0.1.0)

Supported:

* `petrol`
* `diesel`
* `e85`

Not supported:

* jet fuel / avgas / kerosene
* octane grades (RON91 / RON95 / RON98)

---

## Requirements

* Python **3.11+**
* pip

---

## Installation

Editable install (recommended):

```bash
pip install -e .
```

Or run directly from the repository root:

```bash
python -m egstat.cli -h
```

---

## Quick example

```bash
python -m egstat.cli match \
  --disp-cc 1998 \
  --cyl 4 \
  --redline 8600 \
  --target-power-kw 160 \
  --target-power-rpm 8200 \
  --fuel petrol
```

---

## Documentation

* **`manual.md`** — Full CLI reference for EG-Stat v0.1.0 (modes, flags, assumptions, examples)

---

## Project status

This repository documents **EG-Stat v0.1.0** as a stable beta release.
Future versions may expand fuel modelling, vehicle-based cruise estimation, plotting, and graphical interfaces.
