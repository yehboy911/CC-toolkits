---
name: check-safety
description: >
  Autonomous Security Auditor — proactively intercept and remediate supply-chain
  attacks in Python (PyPI) and JavaScript (npm) environments. Covers litellm
  2026-03-24 (credential exfiltration) and axios 2026-03-31 (cross-platform RAT
  dropper). Invoke manually with /check-safety, or activate proactively when the
  user installs, imports, or pastes a requirements.txt / package.json containing
  a known-malicious package.
origin: custom
---

# Autonomous Security Auditor

## Known Malicious Packages

| Package | Ecosystem | Bad Versions | Incident Date | Threat |
|---------|-----------|--------------|---------------|--------|
| litellm | PyPI | 1.82.7, 1.82.8 | 2026-03-24 | Credential exfiltration on `import` (SSH keys, AWS/GCP/Azure, kubeconfig, env vars, shell history, crypto wallets, CI/CD secrets, DB passwords) |
| axios | npm | 1.14.1, 0.30.4 | 2026-03-31 | RAT dropper via hidden dep `plain-crypto-js@4.2.1`; C2: `sfrclak.com:8000` (`142.11.206.73`) |

> To extend for future incidents: add a row to the table above and update the
> corresponding script constants.

---

## When to Activate

### Reactive (user invokes directly)
- User runs `/check-safety` or `/check-python-safety` or `/check-npm-safety`
- User asks "is litellm safe?", "do I have the bad axios?", "supply chain attack", etc.

### Proactive (intercept automatically)
- User runs or pastes: `pip install litellm`, `npm install axios`, `npm i axios`
- User pastes a `requirements.txt` containing `litellm`
- User pastes a `package.json` or `package-lock.json` containing `axios`
- User mentions "sfrclak.com", "plain-crypto-js", or "com.apple.act.mond"

---

## Script Discovery

Before running inline checks, auto-discover the standalone scripts:

```bash
# litellm checker
find ~ -maxdepth 5 -name "litellm-check-safety.py" 2>/dev/null | head -1

# axios / npm checker
find ~ -maxdepth 5 -name "check-npm-safety.py" 2>/dev/null | head -1
```

If found → use the scripts (they have richer output).
If not found → use the inline fallbacks below.

---

## Execution Protocol

### Phase 1 — Deep Scan

#### 1a. litellm (PyPI)

**Using script (preferred):**
```bash
python3 <DISCOVERED_PATH>/litellm-check-safety.py --json
```

**Inline fallback (no script):**
```python
python3 - <<'EOF'
import sys, subprocess
version = None
try:
    from importlib.metadata import version as v
    version = v("litellm")
except Exception:
    pass
if version is None:
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "show", "litellm"],
                           capture_output=True, text=True, timeout=15)
        for line in r.stdout.splitlines():
            if line.startswith("Version:"):
                version = line.split(":",1)[1].strip()
    except Exception:
        pass
print(f"LITELLM_VERSION:{version or 'NOT_INSTALLED'}")
EOF
```

Scan for dropper .pth file (persists after uninstall):
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

| Detected version | Status |
|---|---|
| `1.82.7` or `1.82.8` | **MALICIOUS** |
| PTH_HITS ≠ NONE | **MALICIOUS** (dropper persists) |
| `NOT_INSTALLED` | **NOT_INSTALLED** |
| anything else | **SAFE** |

#### 1b. axios (npm)

**Using script (preferred):**
```bash
python3 <DISCOVERED_PATH>/check-npm-safety.py --json --dir <project_dir>
```

**Inline fallback — version detection (no npm required):**
```python
python3 - <<'EOF'
import json, sys
from pathlib import Path

project = Path(".")
version = None

# Method 1: installed package manifest
pkg = project / "node_modules" / "axios" / "package.json"
if pkg.exists():
    try:
        version = json.loads(pkg.read_text())["version"]
    except Exception:
        pass

# Method 2: package-lock.json
if version is None:
    lock = project / "package-lock.json"
    if lock.exists():
        try:
            data = json.loads(lock.read_text())
            # v2/v3 format
            entry = data.get("packages", {}).get("node_modules/axios")
            if entry:
                version = entry.get("version")
            # v1 format
            if version is None:
                version = data.get("dependencies", {}).get("axios", {}).get("version")
        except Exception:
            pass

print(f"AXIOS_VERSION:{version or 'NOT_INSTALLED'}")
EOF
```

Check for dropper directory (CRITICAL — persists even after self-cleanup):
```bash
# The dropper self-deletes setup.js and replaces package.json with a clean stub.
# But the DIRECTORY always remains. Its presence = dropper executed.
ls node_modules/plain-crypto-js 2>/dev/null && echo "DROPPER_DIR_FOUND" || echo "DROPPER_DIR_ABSENT"
```

| Detected version | Dropper dir | Status |
|---|---|---|
| `1.14.1` or `0.30.4` | any | **MALICIOUS** |
| any | FOUND | **MALICIOUS** (RAT likely ran) |
| `NOT_INSTALLED` | ABSENT | **NOT_INSTALLED** |
| anything else | ABSENT | **SAFE** |

#### 1c. Forensic Scan (when `--forensic` or explicitly requested)

```bash
# RAT artifacts (per-platform persistence files)
ls -la /Library/Caches/com.apple.act.mond 2>/dev/null && echo "RAT_MACOS"  # macOS
ls -la /tmp/ld.py 2>/dev/null && echo "RAT_LINUX"                           # Linux
# Windows: dir "%PROGRAMDATA%\wt.exe" 2>nul && echo RAT_WIN

# C2 domain in shell history
grep -h "sfrclak.com\|142.11.206.73" ~/.bash_history ~/.zsh_history 2>/dev/null

# Sensitive env vars exposed at install time
python3 -c "
import os
VARS=['AWS_SECRET_ACCESS_KEY','AWS_ACCESS_KEY_ID','GITHUB_TOKEN','KUBECONFIG',
      'OPENAI_API_KEY','ANTHROPIC_API_KEY','NPM_TOKEN','DATABASE_URL']
exposed=[v for v in VARS if os.environ.get(v)]
print('EXPOSED_VARS:' + ','.join(exposed) if exposed else 'EXPOSED_VARS:NONE')
"
```

---

### Phase 2 — Critical Alert

If **any** package returns MALICIOUS, output the high-urgency dashboard:

```
╔══════════════════════════════════════════════════════════════╗
║  🚨  SUPPLY-CHAIN ATTACK CONFIRMED                          ║
╠══════════════════════════════════════════════════════════════╣
║  Risk Level : CRITICAL                                       ║
║  Impact     : <credential exfiltration | RAT deployed>       ║
╚══════════════════════════════════════════════════════════════╝

ATTACK FLOW (axios):
  [npm install axios@1.14.1]
    → [plain-crypto-js@4.2.1 postinstall → setup.js]
    → [sfrclak.com:8000 → platform RAT payload]
    → [setup.js self-deletes] → [RAT orphaned to PID 1, running]

ATTACK FLOW (litellm):
  [import litellm]  ← executes ON EVERY IMPORT
    → [credential harvest: SSH, AWS, GCP, env vars, history, wallets]
    → [exfiltration to attacker C2]
```

---

### Phase 3 — One-Click Remediation & Forensics

#### litellm MALICIOUS
```bash
pip uninstall litellm -y
pip install litellm==1.82.6 --force-reinstall
# Remove dropper if found:
find $(python3 -c 'import site; print(site.getsitepackages()[0])') \
  -name 'litellm_init.pth' -delete
```

#### axios MALICIOUS
```bash
npm install axios@1.14.0        # 1.x users
# npm install axios@0.30.3      # 0.x users
rm -rf node_modules/plain-crypto-js
npm install --ignore-scripts
# Block C2:
echo "0.0.0.0 sfrclak.com" >> /etc/hosts
# Linux: iptables -A OUTPUT -d 142.11.206.73 -j DROP
```

#### If RAT artifact found (axios)
```
⛔  DO NOT CLEAN IN PLACE.
    Rebuild the system from a known-good state.
    The RAT may still be running as a detached background process.
```

#### Credential Rotation Checklist (both attacks)
- **SSH keys** → generate new keypairs; revoke from all servers + GitHub
- **AWS** → IAM → rotate access keys; audit CloudTrail
- **GCP** → IAM → revoke service account keys; check Logs Explorer
- **Azure** → Key Vault → rotate secrets; check Activity Log
- **GitHub/GitLab** → Settings → SSH keys + PATs → revoke all
- **npm tokens** → `npm logout`; revoke all tokens at npmjs.com
- **Kubernetes** → rotate kubeconfig; audit RBAC bindings
- **Databases** → rotate all DB passwords (Postgres, MySQL, Redis, Mongo)
- **CI/CD** → re-roll GitHub Actions / GitLab CI secrets
- **Crypto wallets** → assume seed compromised → transfer to new wallet
- **API keys** → rotate every key visible in env vars or `~/.config/*`
- **.env files** → any secrets in `.env` at install time are compromised

---

## Notes

- **Never `import litellm`** to check its version — that executes the malicious payload.
  Use `importlib.metadata` or `pip show` only.
- The `plain-crypto-js` directory persists after self-cleanup. Package.json will look
  clean (version 4.2.0, no postinstall) — ignore it. **Directory presence = compromise.**
- Exit codes from both scripts: `1` = MALICIOUS, `0` = SAFE/NOT_INSTALLED (CI-friendly).
- C2 domain is `sfrclak.com` (not `sftcluk.com` — common typo).
