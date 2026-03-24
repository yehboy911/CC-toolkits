# Update README.md & CLAUDE.md to Current State

## Context

The project has evolved significantly since v0.1.0 — new modules (`gpl_scanner.py`, `license_patterns.py`, `interactive_menu.py`), redesigned checkpoints (CP06, CP10), new CLI flags (`--config-h`, `--sbom`, `--no-interactive`), and tier-based report grouping. Both README.md and CLAUDE.md are frozen at v0.1.0 and need to reflect the current state so future sessions can pick up seamlessly.

---

## Files Modified

| File | Change |
|------|--------|
| `README.md` | Full rewrite to reflect current features, CLI flags, checkpoint descriptions, tier grouping, module inventory |
| `CLAUDE.md` | Recreate (currently deleted per git status) with updated module map, checkpoint table, design decisions, report structure |

---

## 1. README.md — Updated Sections

### Usage section
Add all current CLI flags:
```
--output / -o FILE      Write report to file (default: stdout)
--exclude / -e DIR      Exclude directory prefix (repeatable)
--config-h FILE         FFmpeg config.h for enhanced GPL/nonfree detection (CP01/CP04)
--sbom FILE             OSC SBOM CSV for GPL/LGPL confirmation (repeatable, CP06/CP10)
--no-interactive        Disable curses menu (for CI/scripts)
```

### "What It Checks" table
Update all 15 checkpoint names and descriptions to current state:
- CP02: now covers GPL+LGPL; GPL+STATIC→FAIL, GPL+SHARED→MANUAL
- CP05: renamed "GPL/LGPL Library Identification"
- CP06: redesigned — two-layer analysis with confirmed GPL components
- CP07: cross-references install targets against test targets + COMPONENT analysis
- CP08: counts inline source_files as traceable
- CP10: **renamed "Extlibs Component Audit"** — discovers pre-compiled OSS under `**/extlibs/**/include/`
- CP12: GPL/LGPL-aware visibility checks
- CP13: prioritizes GPL/LGPL EPs without CONFIGURE_COMMAND
- CP14: expanded LGPL regex
- CP15: labels GPL/LGPL downloads

### New section: "Enhanced Scan Options"
Describe `--config-h` (FFmpeg config.h) and `--sbom` (SBOM CSV) with examples.

### New section: "Interactive Menu"
Explain curses-based checkbox menu; `--no-interactive` for CI; fallback to text input.

### New section: "Report Tier Grouping"
Document the 3-tier structure:
- Tier 1: GPL/LGPL Direct Risk Detection (CP01, CP02, CP04, CP05, CP06)
- Tier 2: Build System Hygiene (CP03, CP07, CP08, CP09, CP10, CP11, CP12)
- Tier 3: External Source Tracking (CP13, CP14, CP15)

### "Report Format" section
Update the example to show tier-based structure (Summary with Per-Tier Breakdown, Checkpoint tables grouped by tier, Action Items grouped by tier).

### New section: "Architecture"
Brief module inventory covering all current `.py` files including the 3 new modules.

---

## 2. CLAUDE.md — Recreate with Current State

Restore as `CLAUDE.md` in project root (not the `osc-evidence-master_CLAUDE.md` backup). Updated content:

### Module Map
Add 3 new modules: `gpl_scanner.py`, `interactive_menu.py`, `license_patterns.py`

### 15 Checkpoints Summary
Update all names/descriptions to current state (same as README table but with "Key CMake Constructs" column)

### Report Sections
Update to reflect tier-based grouping structure:
1. Header
2. Summary + Per-Tier Breakdown
3. Checkpoints grouped by Tier 1/2/3
4. Build Graph Summary
5. Action Items grouped by verdict → tier
6. Parser Warnings

### Key Design Decisions
Keep existing sections (Output Language, N/A vs PASS, Adding a New Legal Rule, Adding a New Checkpoint, ConditionalTracker, SymbolTable) and add:
- **Tier Grouping**: presentation-only concern in `report_generator.py`; `_TIERS` constant maps checkpoint IDs to display tiers
- **GPL Scanner**: `gpl_scanner.py` confirms GPL/LGPL components via LICENSE file scan + SBOM CSV parsing; results injected into CP06/CP10
- **License Patterns**: centralized regex in `license_patterns.py`; all checkpoints use `classify_name()` / `has_gpl_lgpl()`
- **Interactive Menu**: curses-based enhanced scan option selection; `--no-interactive` disables

### CLI flags
Full list of current flags with descriptions.

---

## Verification

```bash
# Confirm both files exist and are non-empty
wc -l README.md CLAUDE.md

# Verify no broken markdown (quick visual check)
head -60 README.md
head -60 CLAUDE.md
```
