# EG-Stat Manual (CLI)

**EG-Stat Version:** 0.1.0

**Manual Version:** 0.1.0

**18/1/2026**

**Author:** Huu Tri (Alvin) Phan (GitHub: K-shii)

**License:** MIT

---

## Quickstart
Install (editable) and run help:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -e .
python -m egstat.cli -h
```

## Overview

EG-Stat is a **core-first engine specification and performance calculator** implemented in Python.
This manual documents the **command-line interface and supported behaviour for version 0.1.0**.

EG-Stat is designed to:

* prioritise transparent engineering assumptions
* separate core calculation logic from user interfaces
* support reproducible analysis via structured outputs

All calculations are **ICE-first** and use **SI units internally**.

---

## Prerequisites

* Python **3.11+** (recommended)
* pip
* (Recommended) Python virtual environment

### Typical setup

From the repository root:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -e .
```

EG-Stat can also be run directly from source:

```bash
python -m egstat.cli <command> [options]
```

---

## CLI usage

Primary invocation:

```bash
python -m egstat.cli <command> [options]
```

Help:

```bash
python -m egstat.cli -h
python -m egstat.cli analyze -h
python -m egstat.cli match -h
python -m egstat.cli design -h
```

---

## Concepts and reference
### Fuels
Supported fuel identifiers:

* `petrol`
* `diesel`
* `e85`

Not supported:

* jet fuel / avgas / kerosene
* octane grades (RON91 / RON95 / RON98)

Notes:

* Fuel selection affects default BSFC assumptions and fuel density.
* Octane effects are not modelled in v0.1.0; use `--bsfc` to approximate efficiency differences.

---

### Cycles
* `4-stroke`
* `2-stroke`

Implementation note: internally, any cycle string starting with `2` is treated as 2‑stroke; all others default to 4‑stroke.

---

## Modes overview

### Analyze

Purpose:

* Generate torque and power curves from a fully specified engine model.

Capabilities:

* Curve generation across RPM
* Peak power / torque / BMEP reporting
* Optional vehicle + drivetrain speed calculations
* JSON save/load and CSV export

---

### Match

Purpose:

* Infer missing engine parameters from partial specifications and performance targets.

Capabilities:

* Peak BMEP inference (unless fixed by user)
* Confidence scoring
* Explicit list of assumptions
* Same curve outputs as Analyze

---

### Design

Purpose:

* Explore feasible engine configurations using targets and engineering constraints.

Capabilities:

* Displacement sweep search
* Cylinder-count exploration
* Constraint filtering (BMEP, piston speed)
* Ranked candidate output

---

## Analyze mode

### Example commands

Basic analysis using displacement and peak BMEP:

```bash
python -m egstat.cli analyze \
  --disp-cc 1998 \
  --redline 8600 \
  --peak-bmep-kpa 1200 \
  --profile balanced \
  --fuel petrol
```

Analysis using bore and stroke:

```bash
python -m egstat.cli analyze \
  --cyl 4 \
  --bore-mm 86 \
  --stroke-mm 86 \
  --redline 7000 \
  --peak-bmep-kpa 1100 \
  --fuel diesel
```

Export torque and power curves to CSV:

```bash
python -m egstat.cli analyze \
  --disp-cc 3500 \
  --redline 6500 \
  --peak-bmep-kpa 1300 \
  --export-csv out/curves.csv
```

---

### Required inputs

When not loading an existing run:

* `--peak-bmep-kpa` **must** be provided

Engine geometry must be defined using **one** of:

* `--disp-cc`
* `--cyl` + `--bore-mm` + `--stroke-mm`

---

### Common options

Engine:

* `--disp-cc`
* `--cyl`
* `--bore-mm`
* `--stroke-mm`
* `--cycle`

RPM range:

* `--idle`
* `--redline`
* `--rpm-min`
* `--rpm-max`
* `--rpm-step`

Assumptions:

* `--profile`
* `--fuel`
* `--bsfc`

Presets (optional):

* `--engine-preset`
* `--vehicle-preset`
* `--gearbox-preset`

I/O:

* `--save-json`
* `--load-json`
* `--recompute`
* `--export-csv`

---

### Vehicle and drivetrain (optional)

If vehicle and drivetrain data are present, Analyze additionally reports:

* per-gear speed at redline
* estimated top speed
* suggested upshift points

Vehicle parameters:

* `--mass-kg`
* `--cd`
* `--fa-m2`
* `--crr`
* `--rho`

Drivetrain parameters:

* `--gears`
* `--final-drive`
* `--tire-radius-m`
* `--drivetrain-eff`

---

## Match mode

### Example commands

Infer missing parameters from performance targets:

```bash
python -m egstat.cli match \
  --disp-cc 1998 \
  --cyl 4 \
  --redline 8600 \
  --target-power-kw 160 \
  --target-power-rpm 8200 \
  --fuel petrol
```

Compare fuels with a fixed BSFC:

```bash
python -m egstat.cli match \
  --disp-cc 1998 \
  --cyl 4 \
  --redline 8600 \
  --target-power-kw 160 \
  --target-power-rpm 8200 \
  --bsfc 270 \
  --fuel e85
```

Save a matched run to JSON:

```bash
python -m egstat.cli match \
  --disp-cc 1998 \
  --cyl 4 \
  --redline 8600 \
  --target-power-kw 160 \
  --target-power-rpm 8200 \
  --fuel petrol \
  --save-json runs/k20_match.json
```

---

## Match mode (reference)

### Key inputs

Partial engine specification:

* `--disp-cc`
* `--cyl`
* `--bore-mm`
* `--stroke-mm`
* `--cycle`
* `--redline`

Targets:

* `--target-power-kw`
* `--target-power-rpm`
* `--target-torque-nm`
* `--target-torque-rpm`

Optional overrides:

* `--peak-bmep-kpa`

Assumptions:

* `--profile`
* `--fuel`
* `--bsfc`
* `--engine-preset`

Outputs:

* completed engine spec
* inferred peak BMEP
* confidence score
* assumption list

---

## Design mode

### Example commands

Search for feasible engine designs under constraints:

```bash
python -m egstat.cli design \
  --target-power-kw 120 \
  --target-power-rpm 6500 \
  --redline 7000 \
  --profile balanced \
  --disp-min-cc 1500 \
  --disp-max-cc 3000 \
  --disp-step-cc 250 \
  --cyls 4 6 \
  --top-n 3 \
  --fuel petrol
```

Export candidate list to CSV:

```bash
python -m egstat.cli design \
  --target-power-kw 180 \
  --disp-min-cc 1500 \
  --disp-max-cc 4000 \
  --cyls 4 6 \
  --export-candidates-csv out/candidates.csv
```

Save best candidate as JSON:

```bash
python -m egstat.cli design \
  --target-power-kw 180 \
  --disp-min-cc 1500 \
  --disp-max-cc 4000 \
  --cyls 4 6 \
  --save-json runs/best_design.json
```

---

## Design mode (reference)

### Required input

* `--target-power-kw`

### Search parameters

* `--disp-min-cc`
* `--disp-max-cc`
* `--disp-step-cc`
* `--cyls`
* `--bmep-max-kpa`
* `--piston-speed-max`
* `--top-n`

### Outputs

* ranked candidate list
* optional CSV export
* optional JSON save of best candidate

---

## Outputs and assumptions

EG-Stat reports:

* displacement (L)
* peak power and torque (+ RPM)
* peak BMEP
* fuel type and BSFC
* fuel consumption estimates:

  * WOT at peak power
  * cruise (fixed 20 kW assumption)
* piston speed at redline (if relevant)

Warnings are issued for mechanically aggressive configurations.

---

## File formats

### JSON (RunFile)

Used for:

* reproducible runs
* reloadable analysis

Stored fields include:

* engine spec
* assumptions
* run configuration
* computed curves and scalars

### CSV

Used for:

* curve export
* design candidate comparison

---

## Testing

From the repository root:

```bash
pytest
```
