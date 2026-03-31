#!/usr/bin/env python3
"""
check-npm-safety.py
===================
Standalone CLI safety checker for the axios npm supply-chain attack.

INCIDENT SUMMARY
----------------
Date     : 2026-03-31
Package  : axios on npm
Bad ver  : 1.14.1 (1.x branch), 0.30.4 (0.x branch)
Impact   : Malicious dependency plain-crypto-js@4.2.1 injected automatically.
           Its postinstall script (setup.js) drops a cross-platform RAT that
           contacts C2 at sfrclak.com:8000, then self-deletes all evidence.
           The directory node_modules/plain-crypto-js/ PERSISTS after cleanup
           and is sufficient evidence the dropper executed.

Source   : StepSecurity incident report 2026-03-31
           https://www.stepsecurity.io/blog/axios-compromised-npm-malicious-rat

Usage
-----
  python3 check-npm-safety.py                    # scan cwd
  python3 check-npm-safety.py --dir /path/proj   # scan specific project
  python3 check-npm-safety.py --json             # machine-readable output
  python3 check-npm-safety.py --forensic         # + forensic RAT artifact scan
"""

import sys
import os
import json
import argparse
import platform
from pathlib import Path

# ─────────────────────────────────────────────
# THREAT INTELLIGENCE — update when new incidents confirmed
# ─────────────────────────────────────────────
AXIOS_MALICIOUS_VERSIONS   = {"1.14.1", "0.30.4"}
AXIOS_SAFE_FOR_1X          = "1.14.0"
AXIOS_SAFE_FOR_0X          = "0.30.3"
AXIOS_DROPPER_PACKAGE      = "plain-crypto-js"          # directory name to scan for
AXIOS_DROPPER_VERSION      = "4.2.1"                    # malicious version
AXIOS_C2_DOMAIN            = "sfrclak.com"              # NOTE: sfrclak, not sftcluk
AXIOS_C2_IP                = "142.11.206.73"
AXIOS_C2_PORT              = 8000
AXIOS_INCIDENT_DATE        = "2026-03-31"

# Platform-specific RAT persistence artifacts (StepSecurity IoCs)
_RAT_ARTIFACTS: dict[str, Path] = {
    "darwin": Path("/Library/Caches/com.apple.act.mond"),
    "linux":  Path("/tmp/ld.py"),
    # Windows: %PROGRAMDATA%\wt.exe — resolved at runtime
}

# Sensitive env vars whose values may have been exfiltrated
SENSITIVE_ENV_VARS = [
    "AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID", "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_KEYFILE_JSON",
    "AZURE_CLIENT_SECRET", "AZURE_CLIENT_ID", "AZURE_TENANT_ID",
    "GITHUB_TOKEN", "GH_TOKEN", "GITLAB_TOKEN", "CI_JOB_TOKEN",
    "KUBECONFIG",
    "DATABASE_URL", "DB_PASSWORD", "POSTGRES_PASSWORD", "MYSQL_PASSWORD",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "NPM_TOKEN",
    "SLACK_TOKEN", "STRIPE_SECRET_KEY", "TWILIO_AUTH_TOKEN",
]

# ─────────────────────────────────────────────
# ANSI color helpers (no external deps)
# ─────────────────────────────────────────────
def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()

USE_COLOR = _supports_color()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def red(t):         return _c("1;31", t)
def green(t):       return _c("1;32", t)
def yellow(t):      return _c("1;33", t)
def cyan(t):        return _c("1;36", t)
def bold(t):        return _c("1", t)
def white_bg_red(t): return _c("1;37;41", t)

# ─────────────────────────────────────────────
# OPTIONAL: upgrade output with `rich` if present
# ─────────────────────────────────────────────
try:
    from rich.console import Console as _RichConsole
    from rich.panel import Panel as _Panel
    from rich.text import Text as _Text
    _rich_console = _RichConsole()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ─────────────────────────────────────────────
# VERSION DETECTION — file-based, no npm subprocess
# ─────────────────────────────────────────────
def _read_json_safe(path: Path) -> dict | None:
    """Parse a JSON file; return None on any error."""
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def get_axios_version(project_dir: Path) -> str | None:
    """
    Detect installed axios version without running npm.

    Strategy (in order):
    1. node_modules/axios/package.json → "version"
    2. package-lock.json v2/v3 → packages["node_modules/axios"]["version"]
    3. package-lock.json v1   → dependencies["axios"]["version"]
    Returns version string or None if axios is not found.
    """
    # Method 1: installed package manifest
    pkg_json = project_dir / "node_modules" / "axios" / "package.json"
    if pkg_json.exists():
        data = _read_json_safe(pkg_json)
        if data and isinstance(data.get("version"), str):
            return data["version"]

    # Method 2: package-lock.json (covers npm workspaces too)
    lockfile = project_dir / "package-lock.json"
    if lockfile.exists():
        lock = _read_json_safe(lockfile)
        if lock:
            # v2 / v3 format
            packages = lock.get("packages", {})
            for key in ("node_modules/axios", f"node_modules{os.sep}axios"):
                entry = packages.get(key)
                if entry and isinstance(entry.get("version"), str):
                    return entry["version"]
            # v1 format
            deps = lock.get("dependencies", {})
            axios_dep = deps.get("axios")
            if axios_dep and isinstance(axios_dep.get("version"), str):
                return axios_dep["version"]

    return None  # axios not found in this project


# ─────────────────────────────────────────────
# DROPPER DIRECTORY DETECTION
# ─────────────────────────────────────────────
def find_dropper_directory(project_dir: Path) -> list[Path]:
    """
    Check for node_modules/plain-crypto-js/ presence.

    CRITICAL: setup.js self-deletes and replaces package.json with a clean stub.
    After cleanup, package.json shows version 4.2.0 with no postinstall — innocent
    looking. But the DIRECTORY always persists. Its presence is definitive evidence
    the dropper executed. Do NOT rely on package.json contents.
    """
    dropper_dir = project_dir / "node_modules" / AXIOS_DROPPER_PACKAGE
    if dropper_dir.is_dir():
        return [dropper_dir]
    return []


# ─────────────────────────────────────────────
# RAT ARTIFACT DETECTION
# ─────────────────────────────────────────────
def find_rat_artifacts() -> dict[str, list[Path]]:
    """
    Scan for platform-specific RAT persistence files left by the dropper.
    Returns dict: {"found": [Path, ...], "checked": [Path, ...]}
    """
    current_platform = platform.system().lower()   # darwin / linux / windows
    checked: list[Path] = []
    found: list[Path] = []

    # macOS and Linux artifacts
    for plat, artifact_path in _RAT_ARTIFACTS.items():
        checked.append(artifact_path)
        if plat == current_platform and artifact_path.exists():
            found.append(artifact_path)

    # Windows: resolve %PROGRAMDATA%
    if current_platform == "windows":
        prog_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        wt_exe = Path(prog_data) / "wt.exe"
        checked.append(wt_exe)
        if wt_exe.exists():
            found.append(wt_exe)

    return {"found": found, "checked": checked}


# ─────────────────────────────────────────────
# C2 HISTORY SCAN
# ─────────────────────────────────────────────
def scan_history_for_c2() -> list[str]:
    """Grep shell history files for C2 domain and IP."""
    history_files = [
        Path.home() / ".bash_history",
        Path.home() / ".zsh_history",
    ]
    c2_indicators = [AXIOS_C2_DOMAIN, AXIOS_C2_IP]
    hits: list[str] = []
    for hf in history_files:
        if not hf.exists():
            continue
        try:
            lines = hf.read_text(errors="replace").splitlines()
            for i, line in enumerate(lines, 1):
                for indicator in c2_indicators:
                    if indicator in line:
                        hits.append(f"[{hf.name}:{i}] {line.strip()[:120]}")
                        break
        except Exception:
            pass
    return hits


# ─────────────────────────────────────────────
# FORENSIC AUDIT
# ─────────────────────────────────────────────
def list_exposed_env_vars() -> dict[str, str]:
    """Return sensitive env vars currently set (values masked)."""
    exposed: dict[str, str] = {}
    for var in SENSITIVE_ENV_VARS:
        val = os.environ.get(var)
        if val:
            exposed[var] = val[:4] + "***" if len(val) > 4 else "***"
    return exposed


def run_forensic_audit(project_dir: Path) -> dict:
    """Run full forensic audit; return structured results."""
    rat     = find_rat_artifacts()
    c2_hits = scan_history_for_c2()
    env     = list_exposed_env_vars()
    return {
        "rat_artifacts_found":   [str(p) for p in rat["found"]],
        "rat_artifacts_checked": [str(p) for p in rat["checked"]],
        "c2_history_hits":       c2_hits,
        "exposed_env_vars":      list(env.keys()),
        "exposed_env_vars_masked": env,
    }


# ─────────────────────────────────────────────
# CORE CHECK FUNCTION
# ─────────────────────────────────────────────
def _safe_version_for(version: str) -> str:
    """Return recommended safe version based on major branch."""
    if version and version.startswith("0."):
        return AXIOS_SAFE_FOR_0X
    return AXIOS_SAFE_FOR_1X


def check_axios_safety(project_dir: Path, quiet: bool = False) -> dict:
    """
    Full axios safety check.

    result keys:
      status          : "MALICIOUS" | "SAFE" | "NOT_INSTALLED"
      version         : str | None
      malicious_pth   : list[str]   — dropper dir + RAT artifact paths
      fix_commands    : list[str]   — commands to run if malicious
      message         : str         — human-readable summary
      c2_hits         : list[str]   — shell history C2 matches
    """
    version       = get_axios_version(project_dir)
    dropper_dirs  = find_dropper_directory(project_dir)
    dropper_strs  = [str(p) for p in dropper_dirs]

    # ── NOT INSTALLED ──────────────────────────────────────────────────────
    if version is None and not dropper_dirs:
        result = {
            "status":        "NOT_INSTALLED",
            "version":       None,
            "malicious_pth": [],
            "fix_commands":  [],
            "message":       "axios not found in this project. No risk from this attack.",
            "c2_hits":       [],
        }
        if not quiet:
            _print_not_installed()
        return result

    # ── MALICIOUS — version match OR dropper dir found ─────────────────────
    is_malicious = (version in AXIOS_MALICIOUS_VERSIONS) or bool(dropper_dirs)
    if is_malicious:
        safe_ver = _safe_version_for(version or "1")
        fix_commands = [
            f"npm install axios@{safe_ver}",
            "rm -rf node_modules/plain-crypto-js",
            "npm install --ignore-scripts",
            f"echo '0.0.0.0 {AXIOS_C2_DOMAIN}' >> /etc/hosts",
            f"# Linux only: iptables -A OUTPUT -d {AXIOS_C2_IP} -j DROP",
        ]
        result = {
            "status":        "MALICIOUS",
            "version":       version,
            "malicious_pth": dropper_strs,
            "fix_commands":  fix_commands,
            "message": (
                f"CRITICAL: axios {version or 'unknown'} is a known supply-chain attack version "
                f"(or dropper directory found). "
                f"A RAT was deployed via plain-crypto-js@{AXIOS_DROPPER_VERSION}. "
                f"C2: {AXIOS_C2_DOMAIN}:{AXIOS_C2_PORT}. Remediate immediately."
            ),
            "c2_hits":       [],
        }
        if not quiet:
            _print_emergency_banner(version, dropper_dirs)
            _print_fix_instructions(safe_ver)
        return result

    # ── SAFE ───────────────────────────────────────────────────────────────
    safe_ver = _safe_version_for(version)
    result = {
        "status":        "SAFE",
        "version":       version,
        "malicious_pth": [],
        "fix_commands":  [],
        "message": (
            f"axios {version} is safe. "
            f"Not in malicious set {sorted(AXIOS_MALICIOUS_VERSIONS)}. "
            f"Recommend pinning axios@{safe_ver} in package.json."
        ),
        "c2_hits":       [],
    }
    if not quiet:
        _print_safe_banner(version, safe_ver)
    return result


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────
def _print_separator(char="═", width=62):
    print(char * width)


def _print_not_installed():
    if HAS_RICH:
        _rich_console.print(_Panel(
            f"[bold green]  ✔  axios not found — no risk from this attack.\n\n"
            f"[yellow]  If you install axios in future, pin: axios@{AXIOS_SAFE_FOR_1X}",
            border_style="green"
        ))
    else:
        print()
        print(green(bold("  ✔  axios not found in this project — no risk from this attack.")))
        print(yellow(f"     If you install in future, pin: axios@{AXIOS_SAFE_FOR_1X}"))
        print()


def _print_emergency_banner(version: str | None, dropper_dirs: list[Path]):
    ver_str = version or "unknown"
    if HAS_RICH:
        msg = _Text()
        msg.append("🚨  CRITICAL SUPPLY-CHAIN COMPROMISE DETECTED  🚨\n\n", style="bold white on red")
        msg.append(f"  Installed axios version   : {ver_str}\n", style="bold red")
        msg.append(f"  Known malicious versions  : {', '.join(sorted(AXIOS_MALICIOUS_VERSIONS))}\n", style="bold red")
        msg.append(f"  C2 server                 : {AXIOS_C2_DOMAIN}:{AXIOS_C2_PORT}\n", style="bold red")
        msg.append(f"  C2 IP                     : {AXIOS_C2_IP}\n\n", style="bold red")
        msg.append("  ATTACK FLOW:\n", style="bold yellow")
        msg.append(
            "  [npm install axios] → [plain-crypto-js postinstall] → [setup.js RAT dropper]\n"
            f"      → [sfrclak.com:{AXIOS_C2_PORT}] → [platform RAT payload delivered]\n"
            "      → [setup.js self-deletes] → [RAT runs in background]\n\n",
            style="yellow"
        )
        if dropper_dirs:
            msg.append("  ⚠  DROPPER DIRECTORY FOUND (evidence RAT executed):\n", style="bold red")
            for d in dropper_dirs:
                msg.append(f"    → {d}\n", style="red")
        _rich_console.print(_Panel(msg, border_style="bold red", expand=True))
    else:
        print()
        print(white_bg_red("  " + "!" * 58 + "  "))
        print(white_bg_red("  🚨  CRITICAL SUPPLY-CHAIN COMPROMISE DETECTED  🚨       "))
        print(white_bg_red("  " + "!" * 58 + "  "))
        print()
        print(red(f"  Installed version  : {bold(ver_str)}"))
        print(red(f"  Malicious versions : {bold(', '.join(sorted(AXIOS_MALICIOUS_VERSIONS)))}"))
        print(red(f"  C2 server          : {bold(AXIOS_C2_DOMAIN + ':' + str(AXIOS_C2_PORT))}"))
        print(red(f"  C2 IP              : {bold(AXIOS_C2_IP)}"))
        print()
        print(yellow("  ATTACK FLOW:"))
        print(yellow("  [npm install axios]"))
        print(yellow(f"    → [plain-crypto-js@{AXIOS_DROPPER_VERSION} postinstall → setup.js RAT dropper]"))
        print(yellow(f"    → [C2: {AXIOS_C2_DOMAIN}:{AXIOS_C2_PORT} → platform payload delivered]"))
        print(yellow("    → [setup.js self-deletes evidence] → [RAT runs in background]"))
        print()
        if dropper_dirs:
            print(red(bold("  ⚠  DROPPER DIRECTORY FOUND — RAT likely executed:")))
            for d in dropper_dirs:
                print(red(f"     → {d}"))
        print()


def _print_fix_instructions(safe_ver: str):
    _print_separator()
    print(bold(cyan("  ONE-CLICK REMEDIATION — run these commands NOW:")))
    _print_separator()
    print()
    print(yellow("  Step 1 — Downgrade axios to last clean version:"))
    print(bold(f"    npm install axios@{safe_ver}"))
    print()
    print(yellow("  Step 2 — Remove the dropper package directory:"))
    print(bold(f"    rm -rf node_modules/{AXIOS_DROPPER_PACKAGE}"))
    print()
    print(yellow("  Step 3 — Reinstall with post-install scripts disabled:"))
    print(bold("    npm install --ignore-scripts"))
    print()
    print(yellow("  Step 4 — Block C2 at network level:"))
    print(bold(f"    echo '0.0.0.0 {AXIOS_C2_DOMAIN}' >> /etc/hosts"))
    print(bold(f"    # Linux: iptables -A OUTPUT -d {AXIOS_C2_IP} -j DROP"))
    print()
    print(red(bold("  ⚠  IF RAT ARTIFACTS FOUND — DO NOT CLEAN IN PLACE:")))
    print(red("     Rebuild from a known-good state. The RAT may still be running."))
    print()
    print(red(bold("  ⚠  ROTATE ALL CREDENTIALS IMMEDIATELY:")))
    credentials = [
        "SSH keys       → generate new keypairs, revoke from all servers/GitHub",
        "AWS            → IAM → rotate access keys, audit CloudTrail",
        "GCP            → IAM → revoke service account keys, audit logs",
        "Azure          → rotate secrets in Key Vault, check Activity Log",
        "GitHub/GitLab  → Settings → SSH keys + PATs → revoke all",
        "npm tokens     → npm logout; revoke all tokens",
        "Kubernetes     → rotate kubeconfig, check RBAC bindings",
        "Database PWDs  → rotate all DB passwords",
        "CI/CD secrets  → re-roll all GitHub Actions / GitLab CI secrets",
        ".env files     → any secrets in .env at install time are compromised",
    ]
    for item in credentials:
        print(red(f"    • {item}"))
    print()
    _print_separator()


def _print_safe_banner(version: str, safe_ver: str):
    if HAS_RICH:
        msg = _Text()
        msg.append(f"  ✔  axios {version} — SAFE\n\n", style="bold green")
        msg.append(f"  Not in malicious set: {', '.join(sorted(AXIOS_MALICIOUS_VERSIONS))}\n", style="green")
        msg.append(f"  No dropper directory (node_modules/{AXIOS_DROPPER_PACKAGE}/) found.\n\n", style="green")
        msg.append(f"  Incident date: {AXIOS_INCIDENT_DATE}\n\n", style="dim")
        msg.append(f"  Recommendation: pin  axios@{safe_ver}  in package.json\n", style="yellow")
        _rich_console.print(_Panel(msg, border_style="bold green", expand=False))
    else:
        print()
        print(green(bold(f"  ✔  axios {version} — SAFE")))
        print(green(f"     Not in malicious set: {', '.join(sorted(AXIOS_MALICIOUS_VERSIONS))}"))
        print(green(f"     No dropper directory found: node_modules/{AXIOS_DROPPER_PACKAGE}/"))
        print(yellow(f"     Recommendation: pin  axios@{safe_ver}  in package.json"))
        print()


def _print_forensic_report(forensic: dict):
    print()
    print("─" * 62)
    print(bold(cyan("  FORENSIC AUDIT")))
    print("─" * 62)

    # RAT artifacts
    rat_found = forensic["rat_artifacts_found"]
    if rat_found:
        print(red(bold(f"\n  ☠  RAT ARTIFACTS FOUND ({len(rat_found)}):")))
        for p in rat_found:
            print(red(f"     → {p}"))
        print(red(bold("\n  SYSTEM IS ACTIVELY COMPROMISED.")))
        print(red("  Do NOT attempt to clean in place. Rebuild from a known-good image."))
    else:
        print(green(f"\n  ✔  No RAT persistence artifacts found"))
        print(green(f"     Checked: {', '.join(forensic['rat_artifacts_checked'])}"))

    # C2 history hits
    c2_hits = forensic["c2_history_hits"]
    if c2_hits:
        print(yellow(f"\n  [!] Shell history C2 hits ({len(c2_hits)}):"))
        for h in c2_hits[:10]:
            print(f"      {h}")
        if len(c2_hits) > 10:
            print(f"      … and {len(c2_hits) - 10} more")
    else:
        print(green(f"\n  ✔  Shell history — no C2 domain/IP hits ({AXIOS_C2_DOMAIN}, {AXIOS_C2_IP})"))

    # Exposed env vars
    env_masked = forensic["exposed_env_vars_masked"]
    if env_masked:
        print(red(f"\n  ☠  EXPOSED CREDENTIALS IN ENVIRONMENT ({len(env_masked)} found):"))
        print(red("     These were accessible to the RAT dropper:"))
        for var, masked in env_masked.items():
            print(red(f"     {var}={masked}"))
        print(yellow("\n     → Rotate ALL of these credentials immediately."))
    else:
        print(green("\n  ✔  No high-value credentials found in environment"))

    print()
    print("─" * 62)


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description=(
            "Check whether the installed axios is affected by the 2026-03-31 "
            "npm supply-chain attack (RAT dropper via plain-crypto-js)."
        )
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output machine-readable JSON instead of human-readable text."
    )
    parser.add_argument(
        "--forensic", action="store_true",
        help="Run post-infection forensic scan: RAT artifacts, C2 history, exposed env vars."
    )
    parser.add_argument(
        "--dir", default=".",
        help="Project directory to scan (default: current directory)."
    )
    args = parser.parse_args()

    project_dir = Path(args.dir).resolve()

    if not args.json:
        _print_separator()
        print(bold(cyan("  axios npm Supply-Chain Safety Checker")))
        print(f"  Incident: {AXIOS_INCIDENT_DATE}  |  Bad versions: {', '.join(sorted(AXIOS_MALICIOUS_VERSIONS))}")
        print(f"  Scanning: {project_dir}")
        _print_separator()

    result = check_axios_safety(project_dir, quiet=args.json)

    # Forensic scan
    if args.forensic:
        forensic = run_forensic_audit(project_dir)
        result["forensic"] = forensic
        if not args.json:
            _print_forensic_report(forensic)

    if args.json:
        print(json.dumps(result, indent=2))

    # Exit code: 1 if malicious — CI pipelines can fail on this
    sys.exit(1 if result["status"] == "MALICIOUS" else 0)


if __name__ == "__main__":
    main()
