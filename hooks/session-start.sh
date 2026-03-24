#!/usr/bin/env bash
# session-start.sh — SessionStart lifecycle hook
# Prints domain context reminder at the start of each Claude Code session
# Exit 0 = allow (always)

cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║           CLAUDE CODE SESSION — DOMAIN CONTEXT              ║
╠══════════════════════════════════════════════════════════════╣
║  User:    Owen Yeh — Senior QE / OSC Compliance, Lenovo     ║
║  Domain:  Firmware open-source compliance (SBOM, GPL/LGPL)  ║
║  Stack:   Pure Python (stdlib only), CMake/C/C++ analysis   ║
╠══════════════════════════════════════════════════════════════╣
║  Active Projects:                                            ║
║  • boost-scanner      CMakeLists.txt Boost dep → SBOM       ║
║  • osc-evidence       GPL/LGPL 15-checkpoint evidence gen   ║
║  • OSC-workflow       Spectra spec-driven compliance flows   ║
║  • SBOM-Checker       SBOM validation, CSV vs source tree   ║
║  • Open-Source-Analysis  5-agent OSC auditing pipeline      ║
╠══════════════════════════════════════════════════════════════╣
║  Workflow Reminders:                                         ║
║  • TDD first — write tests before implementation            ║
║  • pathlib over os.path; type hints on all signatures       ║
║  • No hardcoded absolute paths                              ║
║  • Verify syntax after edits (python3 -m py_compile)        ║
║  • /clear after each major milestone                        ║
╚══════════════════════════════════════════════════════════════╝
EOF

exit 0
