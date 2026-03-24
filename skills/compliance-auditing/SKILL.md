---
name: compliance-auditing
description: Use this skill for firmware open-source compliance auditing tasks: SBOM generation from CMake, GPL/LGPL checkpoint evaluation (CP-01 through CP-15), tiered evidence collection, and NTIA minimum elements validation.
origin: custom
---

# Firmware Open-Source Compliance Auditing

## When to Activate

- Running SBOM generation or validation against a firmware source tree
- Evaluating GPL/LGPL license obligations for C/C++ components
- Working on checkpoint evidence (CP-01 through CP-15) at any tier
- Scanning CMakeLists.txt for Boost or third-party dependency discovery
- Validating SBOM CSV output against NTIA minimum elements
- Orchestrating the 5-agent Open-Source-Analysis pipeline

## Core Principles

### 1. Compliance Tier Model

| Tier | Scope | Key Outputs |
|---|---|---|
| Tier 1 | Component identification | SBOM (package name, version, license) |
| Tier 2 | License obligation analysis | GPL/LGPL linking evidence, source distribution confirmation |
| Tier 3 | Binary/firmware-level evidence | Binary scan output, XCC-specific format, redistribution artifacts |

- Never conflate tier evidence. A Tier-3 change does not automatically satisfy Tier-1 or Tier-2 gaps.
- Always specify which tier is affected in commit messages, PR descriptions, and reports.

### 2. Checkpoint Reference (CP-01 – CP-15)

| Checkpoint | Topic |
|---|---|
| CP-01 | SBOM completeness — all distributed packages identified |
| CP-02 | License identification — SPDX expression per component |
| CP-03 | Version pinning — exact versions in SBOM |
| CP-04 | Source availability — source archive links or internal paths |
| CP-05 | GPL propagation check — static/dynamic linking analysis |
| CP-06 | LGPL compliance — dynamic linking vs. static linking distinction |
| CP-07 | LGPL-2.1-only vs. LGPL-2.1-or-later classification |
| CP-08 | Tier-2 evidence package — linking evidence for LGPL components |
| CP-09 | Copyright notice preservation |
| CP-10 | License text inclusion in distribution |
| CP-11 | CMake dependency graph completeness |
| CP-12 | Boost component version and license mapping |
| CP-13 | Third-party notices file |
| CP-14 | Internal review sign-off |
| CP-15 | Binary scan evidence (Tier-3, XCC firmware) |

When discussing or modifying evidence, always reference the checkpoint number (e.g., `CP-07`) explicitly.

### 3. SBOM Minimum Elements (NTIA)

Every SBOM entry must include:
- **Supplier name** — organization providing the component
- **Component name** — package name
- **Version** — exact version string
- **Unique identifier** — PURL or CPE
- **Dependency relationship** — direct or transitive
- **Author of SBOM data** — who generated this entry
- **Timestamp** — generation datetime (ISO 8601)
- **License expression** (SPDX) — required beyond NTIA minimum for GPL/LGPL compliance

Missing fields are a CP-01 or CP-02 finding.

### 4. CMake Dependency Scanning Rules

- Parse `find_package()`, `FetchContent_Declare()`, `add_subdirectory()`, and `target_link_libraries()` calls
- Treat `PRIVATE` linking as no-propagation; treat `PUBLIC`/`INTERFACE` as potential GPL propagation
- Record Boost component granularity: `Boost::filesystem`, `Boost::regex` etc. — not just `Boost`
- Flag any `FetchContent` that pins a commit hash without a version tag (CP-03 finding)

### 5. GPL/LGPL Classification Logic

```
Static link + GPL → GPL propagates to binary → Tier-2 evidence required
Static link + LGPL-2.1-only → must provide object files or allow relink (CP-06, CP-07)
Dynamic link + LGPL → compliant if user can relink (document in CP-08)
Header-only + LGPL → generally no propagation (document rationale in CP-06)
```

- When classifying, cite the SPDX identifier (e.g., `LGPL-2.1-only`, `GPL-2.0-or-later`)
- Do NOT use informal shorthand like "LGPL" without the version — always include version

## Workflow Steps

### Step 1: Pre-Audit Inventory

Before generating or validating any SBOM:
1. Identify the firmware project and target binary (e.g., XCC BMC image)
2. Confirm the CMake build system root (`CMakeLists.txt` location)
3. Note the distribution channel (internal only vs. customer-facing)
4. Determine which tiers are in scope for this audit

### Step 2: CMake Scan (boost-scanner)

```bash
python3 boost_scanner.py --cmake-root <path> --output sbom.csv
```

- Review output for missing version pins (CP-03) and unlabeled licenses (CP-02)
- Verify all Boost components are listed at component granularity (CP-12)
- Check for `FetchContent` dependencies not captured in the main scan (CP-11)

### Step 3: SBOM Validation (SBOM-Checker)

```bash
python3 sbom_checker.py --sbom sbom.csv --source-tree <path>
```

- Findings map to checkpoints: record each finding as `CP-XX: <description>`
- Treat any NTIA missing-field finding as Tier-1 blocker — do not proceed to Tier-2 without resolving
- Export validation report as `sbom_validation_<date>.txt` for audit trail

### Step 4: License Obligation Analysis (osc-evidence)

```bash
python3 osc_evidence.py --sbom sbom.csv --tier 2 --output evidence/
```

- For each GPL/LGPL component, generate a linking evidence file
- CP-05 through CP-08: verify each component has a corresponding evidence entry
- Flag LGPL-2.1-only components separately (CP-07) — they have stricter object-file requirements

### Step 5: Evidence Collection per Tier

**Tier 1 deliverables:**
- `sbom.csv` — NTIA-compliant SBOM
- `third_party_notices.txt` — all copyright notices and license texts
- `license_summary.md` — per-component SPDX expression table

**Tier 2 deliverables:**
- `evidence/linking_analysis.md` — static vs. dynamic linking per component
- `evidence/lgpl_relink_confirmation.md` — LGPL-2.1-only object file availability
- `evidence/gpl_source_availability.md` — GPL source archive locations

**Tier 3 deliverables (XCC only):**
- `evidence/binary_scan_<firmware_version>.txt` — CP-15 binary scan output
- `evidence/xcc_component_map.csv` — binary → source component mapping

### Step 6: 5-Agent Pipeline (Open-Source-Analysis)

The agentic pipeline consists of:
1. **cmake-scanner** — Parses CMakeLists.txt, generates raw dependency list
2. **license-classifier** — Assigns SPDX expressions, flags GPL/LGPL
3. **sbom-generator** — Produces NTIA-compliant CSV
4. **evidence-collector** — Generates tier-specific evidence files
5. **report-synthesizer** — Produces final compliance report

When orchestrating:
- Each agent writes to a shared `workspace/` directory
- Agents are idempotent — safe to re-run after a failure
- If an agent fails, fix that agent's input or logic before re-running the pipeline
- Do NOT skip failed agents and proceed downstream — missing evidence causes CP failures

### Step 7: False Positive Management

When a GPL/LGPL component is flagged but believed to be compliant:
1. Document the rationale in `evidence/false_positive_log.md`
2. Reference the specific SPDX exception (e.g., `GPL-2.0-only WITH Classpath-exception-2.0`)
3. Get sign-off before closing the CP finding (CP-14)
4. Add the component to the known-good fixture list for regression testing

## Common Pitfalls

| Pitfall | Prevention |
|---|---|
| Boost version mismatch between CMake and SBOM | Always derive version from `find_package(Boost VERSION_REQUIRED)` |
| LGPL version conflation | Always use full SPDX ID: `LGPL-2.1-only` vs. `LGPL-2.1-or-later` |
| Missing transitive dependencies | Run `cmake --graphviz` and compare against boost-scanner output |
| Hardcoded firmware binary paths | Use `pathlib.Path` and relative paths — absolute paths break CI |
| Customer SBOM data in commits | Never commit real firmware paths or project names to public repos |
| Tier-3 evidence replacing Tier-2 | Each tier has independent deliverables — neither substitutes the other |

## Owen's Domain Context (Auto-appended)
- Language: Python stdlib-only CLI tools, no web/Docker/ML/databases
- Domain: CMake/C/C++ firmware open-source compliance (SBOM, GPL/LGPL checkpoints)
- Testing: pytest (no existing suites — TDD adoption is the highest-value addition)
- Compliance artifacts require careful review before commit
- Analyze C/C++ firmware but write Python only
