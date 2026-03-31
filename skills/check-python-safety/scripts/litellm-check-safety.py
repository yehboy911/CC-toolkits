#!/usr/bin/env python3
"""
litellm-check-safety.py
=======================
Standalone CLI safety checker for the litellm PyPI supply-chain attack.

INCIDENT SUMMARY
----------------
Date   : 2026-03-24
Package: litellm on PyPI
Bad ver: 1.82.7, 1.82.8
Impact : Malicious code executes ON IMPORT and exfiltrates:
         SSH keys, AWS/GCP/Azure creds, kubeconfig, git creds,
         env vars, shell history, crypto wallets, SSL private keys,
         CI/CD secrets, database passwords — all sent to attacker C2.

Usage
-----
  python3 litellm-check-safety.py          # normal check
  python3 litellm-check-safety.py --json   # machine-readable output
"""

import sys
import os
import subprocess
import json
import sysconfig
import argparse
from pathlib import Path

# ─────────────────────────────────────────────
# CONSTANTS — update this list if new bad versions are discovered
# ─────────────────────────────────────────────
MALICIOUS_VERSIONS = {"1.82.7", "1.82.8"}
SAFE_PINNED_VERSION = "1.82.6"
MALICIOUS_PTH_FILE  = "litellm_init.pth"   # dropper left by the attack
INCIDENT_DATE       = "2026-03-24"

# ─────────────────────────────────────────────
# ANSI color helpers (no external deps required)
# ─────────────────────────────────────────────
def _supports_color() -> bool:
    """Return True when the terminal likely renders ANSI escapes."""
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()

USE_COLOR = _supports_color()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def red(t):    return _c("1;31", t)
def green(t):  return _c("1;32", t)
def yellow(t): return _c("1;33", t)
def cyan(t):   return _c("1;36", t)
def bold(t):   return _c("1", t)
def white_bg_red(t): return _c("1;37;41", t)   # white text on red bg — max alarm

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
# VERSION DETECTION
# ─────────────────────────────────────────────
def get_litellm_version() -> str | None:
    """
    Try importlib.metadata first (fast, no subprocess).
    Fall back to `pip show litellm` for editable / unusual installs.
    Returns version string or None if litellm is not installed.
    """
    # Method 1: importlib.metadata (Python 3.8+)
    try:
        from importlib.metadata import version, PackageNotFoundError
        return version("litellm")
    except Exception:
        pass

    # Method 2: subprocess pip show
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "litellm"],
            capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass

    return None   # litellm not found


# ─────────────────────────────────────────────
# PTH FILE SCAN — secondary indicator of compromise
# ─────────────────────────────────────────────
def find_malicious_pth_files() -> list[Path]:
    """
    Scan all site-packages directories for the known dropper file
    `litellm_init.pth` deposited by the malicious versions.
    """
    found: list[Path] = []
    # Collect all known site-packages paths for the running interpreter
    candidate_dirs: set[Path] = set()

    # sysconfig paths
    for scheme_path in sysconfig.get_paths().values():
        candidate_dirs.add(Path(scheme_path))

    # site module paths
    try:
        import site
        for p in site.getsitepackages():
            candidate_dirs.add(Path(p))
        user_site = site.getusersitepackages()
        if user_site:
            candidate_dirs.add(Path(user_site))
    except Exception:
        pass

    for directory in candidate_dirs:
        pth = directory / MALICIOUS_PTH_FILE
        if pth.exists():
            found.append(pth)

    return found


# ─────────────────────────────────────────────
# FORENSIC AUDIT (only with --forensic flag)
# ─────────────────────────────────────────────
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

# Shell patterns that indicate post-infection exfiltration activity
_SUSPICIOUS_HISTORY_PATTERNS = [
    "curl", "wget", "python3 -c", "bash -c", "eval $(", "exec(",
    "base64 -d", "|sh", "| sh", "|bash", "| bash",
]


def scan_shell_history_for_suspicious() -> list[str]:
    """Scan ~/.bash_history and ~/.zsh_history for suspicious shell patterns."""
    history_files = [
        Path.home() / ".bash_history",
        Path.home() / ".zsh_history",
    ]
    hits: list[str] = []
    for hf in history_files:
        if not hf.exists():
            continue
        try:
            lines = hf.read_text(errors="replace").splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                for pat in _SUSPICIOUS_HISTORY_PATTERNS:
                    if pat in stripped:
                        hits.append(f"[{hf.name}:{i}] {stripped[:120]}")
                        break
        except Exception:
            pass
    return hits


def scan_authorized_keys() -> list[str]:
    """Return non-comment lines from ~/.ssh/authorized_keys."""
    ak = Path.home() / ".ssh" / "authorized_keys"
    if not ak.exists():
        return []
    try:
        return [
            ln.strip() for ln in ak.read_text(errors="replace").splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
    except Exception:
        return []


def list_exposed_sensitive_env_vars() -> dict[str, str]:
    """Return sensitive env vars currently set, with values masked."""
    exposed: dict[str, str] = {}
    for var in SENSITIVE_ENV_VARS:
        val = os.environ.get(var)
        if val:
            exposed[var] = val[:4] + "***" if len(val) > 4 else "***"
    return exposed


def print_forensic_report(
    history_hits: list[str],
    auth_keys: list[str],
    env_vars: dict[str, str],
) -> None:
    """Print the forensic audit section."""
    print()
    print("─" * 62)
    print(bold(cyan("  FORENSIC AUDIT")))
    print("─" * 62)

    # Shell history
    if history_hits:
        print(yellow(f"\n  [!] Shell history — {len(history_hits)} suspicious line(s):"))
        for line in history_hits[:10]:
            print(f"      {line}")
        if len(history_hits) > 10:
            print(f"      … and {len(history_hits) - 10} more")
    else:
        print(green("\n  ✔  Shell history — no suspicious patterns detected"))

    # Authorized keys
    if auth_keys:
        print(yellow(f"\n  [!] ~/.ssh/authorized_keys — {len(auth_keys)} key(s) present:"))
        print(yellow("      Review manually for unauthorized entries:"))
        for k in auth_keys:
            parts = k.split()
            display = " ".join([parts[0]] + ["<key>"] + parts[2:3]) if len(parts) >= 2 else k[:80]
            print(f"      {display}")
    else:
        print(green("\n  ✔  ~/.ssh/authorized_keys — not found or empty"))

    # Exposed env vars
    if env_vars:
        print(red(f"\n  ☠  EXPOSED CREDENTIALS IN ENVIRONMENT ({len(env_vars)} found):"))
        print(red("      These were accessible to the malicious package:"))
        for var, masked in env_vars.items():
            print(red(f"      {var}={masked}"))
        print(yellow("\n      → Rotate ALL of these credentials immediately."))
    else:
        print(green("\n  ✔  No high-value credentials found in environment"))

    print()
    print("─" * 62)


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────
def print_separator(char="═", width=62):
    print(char * width)

def print_emergency_banner(version: str, pth_files: list[Path]):
    """Maximum-visibility alarm output."""
    if HAS_RICH:
        # Rich panel — bright red, impossible to miss
        msg = _Text()
        msg.append("🚨  CRITICAL SUPPLY-CHAIN COMPROMISE DETECTED  🚨\n\n", style="bold white on red")
        msg.append(f"  Installed litellm version : {version}\n", style="bold red")
        msg.append(f"  Known malicious versions  : {', '.join(sorted(MALICIOUS_VERSIONS))}\n\n", style="bold red")
        msg.append("  ON IMPORT this version EXFILTRATES:\n", style="bold yellow")
        for item in [
            "SSH private keys (~/.ssh/)",
            "AWS / GCP / Azure credentials",
            "Kubernetes configs (kubeconfig)",
            "Git credentials & tokens",
            "All environment variables (API keys, secrets)",
            "Shell history (~/.bash_history, ~/.zsh_history)",
            "Crypto wallet files",
            "SSL / TLS private keys",
            "CI/CD secrets (GitHub Actions, GitLab, etc.)",
            "Database passwords",
        ]:
            msg.append(f"    ✗ {item}\n", style="red")
        _rich_console.print(_Panel(msg, border_style="bold red", expand=True))
    else:
        # Pure ANSI fallback
        print()
        print(white_bg_red("  " + "!" * 58 + "  "))
        print(white_bg_red("  🚨  CRITICAL SUPPLY-CHAIN COMPROMISE DETECTED  🚨       "))
        print(white_bg_red("  " + "!" * 58 + "  "))
        print()
        print(red(f"  Installed version  : {bold(version)}"))
        print(red(f"  Malicious versions : {bold(', '.join(sorted(MALICIOUS_VERSIONS)))}"))
        print()
        print(yellow("  ON IMPORT this version EXFILTRATES:"))
        for item in [
            "SSH private keys (~/.ssh/)",
            "AWS / GCP / Azure credentials",
            "Kubernetes configs (kubeconfig)",
            "Git credentials & tokens",
            "All environment variables (API keys, secrets)",
            "Shell history (~/.bash_history, ~/.zsh_history)",
            "Crypto wallet files",
            "SSL / TLS private keys",
            "CI/CD secrets (GitHub Actions, GitLab, etc.)",
            "Database passwords",
        ]:
            print(red(f"    ✗ {item}"))
        print()

    if pth_files:
        print(red(bold("\n  [!] MALICIOUS DROPPER FILE ALSO FOUND:")))
        for p in pth_files:
            print(red(f"      → {p}"))
        print(yellow("      Remove with: rm " + " ".join(str(p) for p in pth_files)))
        print()


def print_fix_instructions():
    print_separator()
    print(bold(cyan("  ONE-CLICK FIX — run these commands NOW:")))
    print_separator()
    print()
    print(yellow("  Step 1 — Remove the malicious package:"))
    print(bold("    pip uninstall litellm -y"))
    print()
    print(yellow("  Step 2 — Reinstall the last safe version:"))
    print(bold(f"    pip install litellm=={SAFE_PINNED_VERSION} --force-reinstall"))
    print()
    print(yellow("  Step 3 — Remove dropper .pth file if present:"))
    print(bold(f"    find $(python -c 'import site; print(site.getsitepackages()[0])') "
               f"-name '{MALICIOUS_PTH_FILE}' -delete"))
    print()
    print(red(bold("  ⚠  ROTATE ALL CREDENTIALS IMMEDIATELY:")))
    credentials_to_rotate = [
        "SSH keys       → generate new keypairs, revoke old ones from all servers",
        "AWS            → IAM → rotate access keys, check CloudTrail for anomalies",
        "GCP            → IAM → revoke service account keys, audit logs",
        "Azure          → rotate secrets in Key Vault, check Activity Log",
        "GitHub/GitLab  → Settings → SSH keys + Personal access tokens → revoke all",
        "Kubernetes     → rotate kubeconfig credentials, check RBAC bindings",
        "Database PWDs  → rotate all DB passwords (MySQL, Postgres, Redis, Mongo…)",
        "CI/CD secrets  → re-roll all GitHub Actions / GitLab CI environment secrets",
        "Crypto wallets → assume wallet seed compromised — transfer funds to new wallet",
        "API keys       → rotate every API key visible in env vars or ~/.config",
    ]
    for item in credentials_to_rotate:
        print(red(f"    • {item}"))
    print()
    print_separator()


def print_safe_banner(version: str):
    """Green confirmation for safe versions."""
    if HAS_RICH:
        msg = _Text()
        msg.append(f"  ✔  litellm {version} is SAFE\n\n", style="bold green")
        msg.append(f"  Not in known malicious set: {', '.join(sorted(MALICIOUS_VERSIONS))}\n", style="green")
        msg.append(f"  Incident date: {INCIDENT_DATE}\n\n", style="dim")
        msg.append(f"  Recommendation: pin  litellm=={SAFE_PINNED_VERSION}  in requirements.txt\n", style="yellow")
        _rich_console.print(_Panel(msg, border_style="bold green", expand=False))
    else:
        print()
        print(green(bold(f"  ✔  litellm {version} — SAFE")))
        print(green(f"     Not in known malicious set: {', '.join(sorted(MALICIOUS_VERSIONS))}"))
        print(yellow(f"     Recommendation: pin  litellm=={SAFE_PINNED_VERSION}  in requirements.txt"))
        print()


def print_not_installed_banner():
    if HAS_RICH:
        _rich_console.print(_Panel(
            f"[bold green]  ✔  litellm is NOT installed — no risk from this attack.\n\n"
            f"[yellow]  If you install it in future, pin: litellm=={SAFE_PINNED_VERSION}",
            border_style="green"
        ))
    else:
        print()
        print(green(bold("  ✔  litellm is NOT installed — no risk from this attack.")))
        print(yellow(f"     If you install it in future, pin: litellm=={SAFE_PINNED_VERSION}"))
        print()


# ─────────────────────────────────────────────
# CORE CHECK FUNCTION (also used by MCP skill)
# ─────────────────────────────────────────────
def check_litellm_safety(quiet: bool = False) -> dict:
    """
    Performs the full safety check.
    Returns a structured result dict suitable for JSON output or MCP response.

    result keys:
      status          : "MALICIOUS" | "SAFE" | "NOT_INSTALLED"
      version         : str | None
      malicious_pth   : list[str]  — paths of dropper files found
      fix_commands    : list[str]  — commands to run if malicious
      message         : str        — human-readable summary
    """
    version      = get_litellm_version()
    pth_files    = find_malicious_pth_files()
    pth_strs     = [str(p) for p in pth_files]

    fix_commands = [
        "pip uninstall litellm -y",
        f"pip install litellm=={SAFE_PINNED_VERSION} --force-reinstall",
    ]
    if pth_files:
        fix_commands.append(
            "find $(python -c 'import site; print(site.getsitepackages()[0])') "
            f"-name '{MALICIOUS_PTH_FILE}' -delete"
        )

    # ── CASE 1: not installed ──────────────────────────────────────────────
    if version is None and not pth_files:
        result = {
            "status":        "NOT_INSTALLED",
            "version":       None,
            "malicious_pth": pth_strs,
            "fix_commands":  [],
            "message":       "litellm is not installed. No risk from this attack.",
        }
        if not quiet:
            print_not_installed_banner()
        return result

    # ── CASE 2: malicious version or dropper found ─────────────────────────
    is_malicious = (version in MALICIOUS_VERSIONS) or bool(pth_files)
    if is_malicious:
        result = {
            "status":        "MALICIOUS",
            "version":       version,
            "malicious_pth": pth_strs,
            "fix_commands":  fix_commands,
            "message": (
                f"CRITICAL: litellm {version} is a known supply-chain attack version. "
                f"It exfiltrates credentials on import. Uninstall immediately and rotate all secrets."
            ),
        }
        if not quiet:
            print_emergency_banner(version or "unknown", pth_files)
            print_fix_instructions()
        return result

    # ── CASE 3: safe ──────────────────────────────────────────────────────
    result = {
        "status":        "SAFE",
        "version":       version,
        "malicious_pth": pth_strs,
        "fix_commands":  [],
        "message": (
            f"litellm {version} is safe. "
            f"Not in malicious set {sorted(MALICIOUS_VERSIONS)}. "
            f"Recommend pinning litellm=={SAFE_PINNED_VERSION} in requirements.txt."
        ),
    }
    if not quiet:
        print_safe_banner(version)
    return result


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Check whether the installed litellm is affected by the 2026-03-24 supply-chain attack."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output machine-readable JSON instead of human-readable text."
    )
    parser.add_argument(
        "--forensic", action="store_true",
        help="Run post-infection forensic audit: shell history, authorized_keys, exposed env vars."
    )
    args = parser.parse_args()

    print_separator()
    print(bold(cyan("  litellm Supply-Chain Safety Checker")))
    print(f"  Incident: {INCIDENT_DATE}  |  Bad versions: {', '.join(sorted(MALICIOUS_VERSIONS))}")
    print_separator()

    result = check_litellm_safety(quiet=args.json)

    if args.forensic and not args.json:
        history_hits = scan_shell_history_for_suspicious()
        auth_keys    = scan_authorized_keys()
        env_vars     = list_exposed_sensitive_env_vars()
        print_forensic_report(history_hits, auth_keys, env_vars)
    elif args.forensic and args.json:
        history_hits = scan_shell_history_for_suspicious()
        auth_keys    = scan_authorized_keys()
        env_vars     = list_exposed_sensitive_env_vars()
        result["forensic"] = {
            "suspicious_history_lines": history_hits,
            "authorized_keys":          auth_keys,
            "exposed_env_vars":         list(env_vars.keys()),
        }

    if args.json:
        print(json.dumps(result, indent=2))

    # Exit code: 1 if malicious so CI pipelines can fail on this
    sys.exit(1 if result["status"] == "MALICIOUS" else 0)


if __name__ == "__main__":
    main()
