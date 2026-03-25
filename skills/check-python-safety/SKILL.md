---
name: check-python-safety
description: Use this skill to check whether any installed Python packages are affected by known supply-chain attacks. Specifically detects the litellm 2026-03-24 PyPI compromise (versions 1.82.7 and 1.82.8 exfiltrate SSH keys, AWS/GCP/Azure creds, kubeconfig, env vars, shell history, crypto wallets, SSL private keys, CI/CD secrets, and database passwords on import). Invoke manually with /check-python-safety, or proactively when the user runs `pip install litellm`, imports litellm, or asks about Python package safety.
origin: custom
---

# Python Package Supply-Chain Safety Checker

## When to Activate

- User invokes `/check-python-safety` directly
- User runs `pip install litellm` (any version)
- User imports `litellm` in code or a requirements file
- User asks "is litellm safe?", "do I have the bad version?", or similar
- User pastes a `requirements.txt` that includes `litellm`

---

## Known Malicious Packages

| Package | Bad Versions | Incident Date | Exfiltrated Data |
|---|---|---|---|
| litellm | 1.82.7, 1.82.8 | 2026-03-24 | SSH keys, AWS/GCP/Azure creds, kubeconfig, git creds, env vars, shell history, crypto wallets, SSL private keys, CI/CD secrets, DB passwords |

> To extend this skill for future supply-chain incidents, add rows to the table above.

---

## Execution Protocol

Follow these steps **in order**. Do NOT import litellm to check its version — that executes the malicious payload.

### Step 1 — Locate the Standalone Script (Auto-Discover)

Run in sequence, stop at the first hit:

```bash
# 1a. Check current working directory
test -f ./litellm-check-safety.py && echo "FOUND:./litellm-check-safety.py"

# 1b. Search home tree (max depth 4, fast)
find ~ -maxdepth 4 -name "litellm-check-safety.py" 2>/dev/null | head -1
```

If found → proceed to **Step 1c**, then **skip to Step 5**.
If not found → proceed to **Step 2** (inline fallback).

```bash
# 1c. Run the script in JSON mode
python3 <DISCOVERED_PATH> --json
```

Parse the JSON output — it contains `status`, `version`, `malicious_pth`, `fix_commands`, `message`.

---

### Step 2 — Inline Fallback: Detect litellm Version (No Script Needed)

```bash
python3 - <<'EOF'
import sys, subprocess, sysconfig
from pathlib import Path

# --- version detection (NEVER import litellm itself) ---
version = None
try:
    from importlib.metadata import version as pkg_version, PackageNotFoundError
    version = pkg_version("litellm")
except Exception:
    pass

if version is None:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "show", "litellm"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.splitlines():
            if line.startswith("Version:"):
                version = line.split(":",1)[1].strip()
    except Exception:
        pass

print(f"VERSION:{version or 'NOT_INSTALLED'}")
EOF
```

---

### Step 3 — Compare Against Malicious Set

| Detected version | Result |
|---|---|
| `1.82.7` or `1.82.8` | **MALICIOUS** |
| `None` / `NOT_INSTALLED` | **NOT_INSTALLED** |
| anything else | **SAFE** (continue to Step 4) |

---

### Step 4 — Scan for Dropper File

The malicious versions also deposit a `.pth` file that survives `pip uninstall`:

```bash
python3 -c "
import site, sysconfig
from pathlib import Path
dirs = set()
try:
    dirs.update(site.getsitepackages())
    u = site.getusersitepackages()
    if u: dirs.add(u)
except: pass
dirs.update(sysconfig.get_paths().values())
hits = [str(Path(d)/'litellm_init.pth') for d in dirs if (Path(d)/'litellm_init.pth').exists()]
print('PTH_HITS:' + ('|'.join(hits) if hits else 'NONE'))
"
```

If any `PTH_HITS` are returned — treat as **MALICIOUS** regardless of version.

---

### Step 5 — Output Using the Templates Below

Pick the matching template based on status from Steps 1–4.

---

## 🚨 MALICIOUS — Output Template

```
## 🚨 CRITICAL — SUPPLY-CHAIN ATTACK DETECTED

**Installed version:** `<VERSION>`
**Known malicious versions:** `1.82.7`, `1.82.8`
**Incident date:** 2026-03-24

---

### ☠️ What This Version Steals (on every `import litellm`)

- SSH private keys (`~/.ssh/`)
- AWS / GCP / Azure credentials
- Kubernetes `kubeconfig`
- Git credentials and tokens
- **All** environment variables (API keys, secrets)
- Shell history (`~/.bash_history`, `~/.zsh_history`)
- Crypto wallet files
- SSL / TLS private keys
- CI/CD secrets (GitHub Actions, GitLab CI, etc.)
- Database passwords

---

### 🔧 One-Click Fix — Run These Commands NOW

```bash
pip uninstall litellm -y
pip install litellm==1.82.6 --force-reinstall
```

If the dropper `.pth` file was also found:
```bash
find $(python3 -c 'import site; print(site.getsitepackages()[0])') \
  -name 'litellm_init.pth' -delete
```

---

### 🔑 Rotate ALL Credentials Immediately

- **SSH keys** → generate new keypairs; revoke old from every server/GitHub
- **AWS** → IAM → rotate access keys; audit CloudTrail
- **GCP** → IAM → revoke service account keys; check Logs Explorer
- **Azure** → Key Vault → rotate secrets; check Activity Log
- **GitHub/GitLab** → Settings → SSH keys + PATs → revoke all
- **Kubernetes** → rotate kubeconfig; audit RBAC bindings
- **Databases** → rotate all DB passwords (Postgres, MySQL, Redis, Mongo…)
- **CI/CD** → re-roll GitHub Actions / GitLab CI secrets
- **Crypto wallets** → assume seed compromised → transfer funds to new wallet
- **API keys** → rotate every key visible in env vars or `~/.config/*`
```

---

## ✅ SAFE — Output Template

```
## ✅ litellm `<VERSION>` — SAFE

Not in known malicious set (`1.82.7`, `1.82.8`).
No dropper file (`litellm_init.pth`) detected.

**Recommendation:** Pin this version in `requirements.txt`:
```
litellm==1.82.6
```
```

---

## ℹ️ NOT INSTALLED — Output Template

```
## ℹ️ litellm is NOT installed

No risk from the 2026-03-24 supply-chain attack.

**If you install litellm in future, pin the safe version:**
```bash
pip install litellm==1.82.6
```
And add to `requirements.txt`:
```
litellm==1.82.6
```
```

---

## Notes for Claude

- **Never `import litellm`** — that is exactly how the malicious code executes. Use `importlib.metadata` or `pip show` only.
- If both the script and inline fallback fail (e.g., no Python available), tell the user to run: `pip show litellm` and compare the version manually.
- Exit code from the standalone script is `1` for MALICIOUS, `0` for SAFE/NOT_INSTALLED — useful for CI gates.
