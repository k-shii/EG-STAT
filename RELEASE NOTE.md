# EG-Stat Release Notes
---

## v0.2.1 — Maintenance & CLI Bug Fix Update

This is a small maintenance release focused on clarifying CLI entry points and restoring documented behavior.

### Changes
- Clarified and restored console command behavior.
- Guided interactive UI is now explicitly launched via `egstat -ui` / `egstat --ui`.
- Legacy subcommands (`analyze`, `match`, `design`) remain fully scriptable and non-interactive.
- Documentation updated to clarify installation requirements for the `egstat` console command.

### Notes
- No changes to engine models, physics, calculations, or outputs.
- Fully backward compatible with v0.2.0.

---

## v0.2.0 — Guided CLI & UX Overhaul (Major Update)

This release marks the first major usability milestone for EG-Stat.
The core physics and calculation engine remain unchanged from v0.1.x.  
All improvements in v0.2.0 focus on usability, workflow clarity, and robustness, without altering any engineering results.

### ⚠️ Note (v0.2.0)
- During the initial v0.2.0 rollout, console command usage required explicit installation (`pip install -e .`) to enable the `egstat` entry point.
- Legacy CLI functionality itself was not removed, but documentation and entry-point behavior were unclear.
- This has been clarified and resolved in v0.2.1.

### Highlights
- New guided interactive CLI for human-friendly use
- Clear separation between guided UI and legacy CLI
- Stronger input validation and safer file handling
- Major documentation rewrite (manual + README alignment)

### New Features
#### Guided Interactive Mode
- Running `egstat` or `python -m egstat.cli` with no arguments now launches a menu-driven interface
- Step-by-step prompts with defaults and validation
- Automatic return to main menu after each run
- Suitable for exploration, learning, and day-to-day use

#### About / Credits Screen
- Version, author, license, and support information accessible from the UI
- Clear messaging about project scope and roadmap

#### Robust Save & Export Handling
- File extensions (`.json`, `.csv`) are now enforced
- Entering `run` automatically saves as `run.json`
- Invalid extensions are rejected with clear errors
- Parent directories are created automatically

### Compatibility & Legacy Support
#### Legacy CLI Fully Preserved
All v0.1.x commands remain valid and unchanged:

```bash
egstat analyze ...
egstat match ...
egstat design ...
```

---

## v0.1.1
- Repo cleanup: simplified naming/layout
- No functional changes

---

## v0.1.0
- Initial public beta
- Analyze / Match / Design modes
