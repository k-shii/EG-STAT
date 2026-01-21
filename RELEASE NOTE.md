# EG-Stat Release Notes
---
## v0.2.0 — Guided CLI & UX Overhaul (Major Update)

This release marks the first major usability milestone for EG-Stat.
The core physics and calculation engine remain unchanged from v0.1.x.  
All improvements in v0.2.0 focus on usability, workflow clarity, and robustness, without altering any engineering results.

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
