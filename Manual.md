# EG-Stat Manual — Version 0.2.0

**EG-Stat Version:** 0.2.0
**Manual Version:** 0.2.0
**Date:** 21 Jan 2026
**Author:** Huu Tri (Alvin) Phan
**License:** MIT

---

## 1. What is EG-Stat?

EG-Stat is a **command-line engine specification and performance analysis tool**.

It is designed to:

* explore internal combustion engine behaviour using defensible physics
* clearly expose assumptions and inferred values
* work both **interactively (guided UI)** and **non-interactively (legacy CLI)**

The calculation core is unchanged from v0.1.x. Version **0.2.0 focuses on usability**.

---

## 2. How to Start EG-Stat (Important)

EG-Stat can be launched in **multiple valid ways**, depending on what you want to do. This section clarifies the correct entry points and avoids common confusion.

### 2.1 Core Module Entry (`python -m egstat`)

```
python -m egstat
```

This command **only loads the core package** via `__main__.py`.

* It confirms the EG-Stat core is installed and importable
* It does **NOT** start the CLI or guided UI
* It may print a short message such as "core loaded"

Use this only for:

* quick sanity checks
* debugging imports

It is **not** how you normally run EG-Stat.

---

### 2.2 CLI Entry Point (Recommended)

```
python -m egstat.cli
```

This starts the **actual command-line interface**.

Behaviour:

* With **no arguments** → launches the **guided interactive menu**
* With a **subcommand** → runs that mode directly (non-interactive)

This is the correct entry point for almost all users.

---

### 2.3 Guided Mode (Interactive UI)

```
python -m egstat.cli
```

When run with no arguments and a TTY is detected, EG-Stat enters **guided mode**:

* menu-driven navigation
* step-by-step prompts
* loops back to main menu after each run

Equivalent (if installed as a console script):

```
egstat
```

---

### 2.4 Legacy CLI Mode (Direct Commands)

You may run any mode directly without the UI:

```
python -m egstat.cli analyze ...
python -m egstat.cli match ...
python -m egstat.cli design ...
```

In this case:

* the guided UI is skipped
* EG-Stat behaves exactly like v0.1.x
* suitable for scripts, automation, and batch runs

---

### 2.5 Help and Command Discovery

Global help:

```
python -m egstat.cli --help
```

Mode-specific help:

```
python -m egstat.cli analyze --help
python -m egstat.cli match --help
python -m egstat.cli design --help
```

All legacy flags remain supported.

---

---

## 3. Guided Mode — How to Navigate

### 3.1 Main Menu

When guided mode starts, you will see:

```
1) Analyze engine
2) Match (fill missing engine data)
3) Design engine from targets
4) Load previous run (JSON)
5) About / Credits
0) Exit
```

Select an option by number. After completing any action, EG-Stat will ask whether to return to this menu.

---

## 4. Analyze Engine (Guided)

**Use this when:** you already have an engine concept and want to see what it does.

### What Analyze does

* computes torque and power curves
* reports peak torque, power, and BMEP
* estimates fuel consumption
* optionally evaluates vehicle performance

### Guided Analyze flow

You will be prompted for:

1. **Engine definition**

   * displacement *or* bore & stroke
   * cylinder count
   * engine cycle (2‑stroke / 4‑stroke)

2. **RPM limits**

   * idle RPM
   * redline RPM
   * RPM sweep range

3. **Performance intent**

   * peak BMEP (overall engine aggressiveness)
   * VE profile (balanced / torque / top‑end)

4. **Fuel assumptions**

   * fuel type
   * optional BSFC override

5. **Optional vehicle & drivetrain**

   * vehicle mass, drag, rolling resistance
   * gearbox, final drive, tire radius

Defaults are provided for all non-critical inputs.

### Analyze outputs

* summary of inputs
* peak torque and power (+ RPM)
* fuel consumption estimates
* assumptions used
* warnings (if configuration is aggressive)
* ASCII tables and curves (optional)

---

## 5. Match Mode (Fill the Gaps)

**Use this when:** you know some engine details but not all of them.

Match mode allows **incomplete engine specifications**.

### What Match does

* infers missing parameters
* solves for required peak BMEP
* reports confidence and assumptions
* outputs the same curves as Analyze

### Typical use cases

* reverse‑engineering an engine from power figures
* estimating BMEP for a known production engine
* filling missing BSFC or efficiency data

### Guided Match flow

You provide:

* partial engine spec (e.g. displacement + cylinders)
* performance targets (power and/or torque)

EG-Stat fills in the rest and explains what was assumed.

---

## 6. Design Mode (Targets → Engines)

**Use this when:** you want an engine that meets a goal.

### What Design does

* searches across displacement and cylinder counts
* applies engineering constraints
* ranks feasible engine candidates

### Guided Design flow

You will be prompted for:

* target power and/or torque
* redline
* fuel type
* displacement and cylinder constraints
* optional limits (BMEP, piston speed)

The result is a ranked list of candidate engines.

You may export:

* all candidates to CSV
* the best candidate as a JSON run file

---

## 7. Loading and Reusing Runs

EG-Stat can save and reload complete runs as JSON.

### Load run

```
egstat analyze --load-json run.json
```

Loaded runs can be:

* re‑evaluated
* re‑exported
* used as a baseline for further analysis

---

## 8. File Saving Rules (Important)

EG-Stat enforces file extensions:

* `.json` → run files
* `.csv` → curve or candidate exports

If you enter:

* `run` → saved as `run.json`
* `curves` → saved as `curves.csv`

Invalid extensions are rejected with a clear error message.

Parent directories are created automatically.

---

## 9. Legacy CLI Reference (Still Supported)

### Analyze

```
egstat analyze --disp-cc 1998 --cyl 4 --peak-bmep-kpa 1100 --fuel petrol
```

### Match

```
egstat match --disp-cc 2000 --target-power-kw 150 --fuel petrol
```

### Design

```
egstat design --target-power-kw 300 --fuel petrol
```

All flags from v0.1.x remain valid.

---

## 10. Key Concepts (Short Reference)

* **BMEP**: average cylinder pressure representing engine output intensity
* **BSFC**: fuel efficiency (lower is better)
* **VE profile**: shape of the torque curve
* **Cruise fuel**: estimated using a fixed 20 kW load (v0.2.0 limitation)

You do not need to understand these to use EG-Stat, but they explain the results.

---

## 11. Known Limitations (v0.2.0)

* Cruise fuel is a fixed‑load estimate (not speed‑dependent)
* No graphical plots (ASCII only)
* No GUI build yet

---

## 12. About

**EG-Stat v0.2.0**

Engine specification & performance calculator.

This release introduces a guided CLI interface on top of the validated v0.1.x core.

Author: Huu Tri (Alvin) Phan
Contact: [alvinphanhuu@gmail.com](mailto:alvinphanhuu@gmail.com)
GitHub: [https://github.com/k-shii/EG-STAT](https://github.com/k-shii/EG-STAT)

---

End of Manual