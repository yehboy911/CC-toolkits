#!/usr/bin/env node
/**
 * Security Monitor Hook (PreToolUse)
 *
 * Lightweight, zero-dependency scanner for tool inputs.
 * Detects hardcoded secrets, API keys, tokens, passwords,
 * license-sensitive patterns, and dangerous shell commands.
 *
 * Compatible with run-with-flags.js fast path (exports { run }).
 * Exit behavior: logs warnings to stderr, never blocks (exit 0).
 * Set ECC_SECURITY_MONITOR_STRICT=true to block on findings (exit 2).
 */

'use strict';

const MAX_STDIN = 1024 * 1024;

// --- Secret patterns ---
// Each entry: [label, regex, description]
const SECRET_PATTERNS = [
  ['AWS Access Key', /\bAKIA[0-9A-Z]{16}\b/, 'AWS access key ID'],
  ['AWS Secret Key', /(?:aws_secret_access_key|secret_key)\s*[=:]\s*['"]?[A-Za-z0-9/+=]{40}/, 'AWS secret access key'],
  ['GitHub Token', /\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}\b/, 'GitHub personal access token'],
  ['GitLab Token', /\bglpat-[A-Za-z0-9\-_]{20,}\b/, 'GitLab personal access token'],
  ['Generic API Key', /(?:api[_-]?key|apikey)\s*[=:]\s*['"]?[A-Za-z0-9_\-]{20,}['"]?/i, 'Generic API key assignment'],
  ['Generic Secret', /(?:secret|password|passwd|pwd)\s*[=:]\s*['"]?[^\s'"]{8,}['"]?/i, 'Hardcoded secret or password'],
  ['Bearer Token', /\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b/, 'Bearer token in header'],
  ['Private Key', /-----BEGIN\s+(RSA|EC|DSA|OPENSSH)?\s*PRIVATE KEY-----/, 'Private key block'],
  ['Slack Token', /\bxox[bporas]-[0-9]{10,}-[A-Za-z0-9\-]+\b/, 'Slack API token'],
  ['NPM Token', /\bnpm_[A-Za-z0-9]{36}\b/, 'NPM auth token'],
  ['Anthropic Key', /\bsk-ant-[A-Za-z0-9\-_]{40,}\b/, 'Anthropic API key'],
  ['OpenAI Key', /\bsk-[A-Za-z0-9]{48,}\b/, 'OpenAI API key'],
  ['Hex Secret (32+)', /(?:token|key|secret|password)\s*[=:]\s*['"]?[0-9a-f]{32,}['"]?/i, 'Long hex string assigned to secret-like variable'],
];

// --- Dangerous command patterns ---
const DANGEROUS_CMD_PATTERNS = [
  ['rm -rf /', /\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?\/(?:\s|$)/, 'Recursive delete from root'],
  ['chmod 777', /\bchmod\s+777\b/, 'World-writable permissions'],
  ['curl | sh', /\bcurl\b.*\|\s*(?:ba)?sh\b/, 'Piping remote script to shell'],
  ['wget | sh', /\bwget\b.*\|\s*(?:ba)?sh\b/, 'Piping remote script to shell'],
  ['eval()', /\beval\s*\(/, 'Dynamic code evaluation'],
  ['dd of=/dev', /\bdd\b.*\bof=\/dev\//, 'Writing directly to device'],
  ['mkfs', /\bmkfs\b/, 'Filesystem format command'],
  [':(){:|:&};:', /:\(\)\s*\{.*\}/, 'Fork bomb pattern'],
];

// --- License-sensitive patterns ---
const LICENSE_PATTERNS = [
  ['GPL Header', /GNU\s+General\s+Public\s+License/i, 'GPL license text detected'],
  ['LGPL Header', /GNU\s+Lesser\s+General\s+Public\s+License/i, 'LGPL license text detected'],
  ['AGPL Header', /GNU\s+Affero\s+General\s+Public\s+License/i, 'AGPL license text detected'],
  ['License Removal', /remove.*license|delete.*license|strip.*license/i, 'Possible license removal'],
  ['Copyright Removal', /remove.*copyright|delete.*copyright|strip.*copyright/i, 'Possible copyright removal'],
];

/**
 * @param {string} msg
 */
function log(msg) {
  process.stderr.write(`[SecurityMonitor] ${msg}\n`);
}

/**
 * Extract scannable text from a Claude Code tool input payload.
 *
 * @param {object} data - Parsed JSON from stdin
 * @returns {{ text: string, toolName: string }}
 */
function extractContent(data) {
  const toolName = String(data.tool_name || '');
  const toolInput = data.tool_input || {};
  let text = '';

  if (['Write', 'Edit', 'MultiEdit'].includes(toolName)) {
    text = String(toolInput.content || toolInput.new_string || '');
  } else if (toolName === 'Bash') {
    text = String(toolInput.command || '');
  } else if (toolName === 'NotebookEdit') {
    text = String(toolInput.new_source || '');
  }

  return { text, toolName };
}

/**
 * Scan text against a set of patterns.
 *
 * @param {string} text
 * @param {Array} patterns - Array of [label, regex, description]
 * @returns {Array<{label: string, description: string}>}
 */
function scanPatterns(text, patterns) {
  const findings = [];
  for (const [label, regex, description] of patterns) {
    if (regex.test(text)) {
      findings.push({ label, description });
    }
  }
  return findings;
}

/**
 * Core logic — exported for run-with-flags.js fast path.
 *
 * @param {string} rawInput - Raw JSON string from stdin
 * @returns {string} The original input (pass-through)
 */
function run(rawInput) {
  try {
    const data = JSON.parse(rawInput);
    const { text, toolName } = extractContent(data);

    if (!text || text.length < 5) {
      return rawInput;
    }

    const allFindings = [];

    // Always scan for secrets
    const secrets = scanPatterns(text, SECRET_PATTERNS);
    for (const s of secrets) {
      allFindings.push({ severity: 'HIGH', ...s });
    }

    // Scan commands for dangerous patterns
    if (toolName === 'Bash') {
      const dangerous = scanPatterns(text, DANGEROUS_CMD_PATTERNS);
      for (const d of dangerous) {
        allFindings.push({ severity: 'HIGH', ...d });
      }
    }

    // Scan for license-sensitive patterns (informational)
    if (['Write', 'Edit', 'MultiEdit'].includes(toolName)) {
      const license = scanPatterns(text, LICENSE_PATTERNS);
      for (const l of license) {
        allFindings.push({ severity: 'INFO', ...l });
      }
    }

    if (allFindings.length === 0) {
      return rawInput;
    }

    // Report findings
    const strict = String(process.env.ECC_SECURITY_MONITOR_STRICT || '').toLowerCase() === 'true';
    const hasHigh = allFindings.some(f => f.severity === 'HIGH');

    const lines = ['== Security Monitor — Findings ==', ''];
    for (let i = 0; i < allFindings.length; i++) {
      const f = allFindings[i];
      lines.push(`${i + 1}. [${f.severity}] ${f.label}: ${f.description}`);
    }
    lines.push('');

    if (hasHigh && strict) {
      // Block execution — write to stdout for Claude to see
      lines.push('Action blocked. Review and fix the issues above.');
      process.stdout.write(lines.join('\n') + '\n');
      process.exit(2);
    }

    // Non-blocking warning via stderr
    log('\n' + lines.join('\n'));

  } catch {
    // Ignore parse errors — pass through
  }

  return rawInput;
}

// ── stdin entry point (backwards-compatible) ────────────────────
if (require.main === module) {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {
    if (raw.length < MAX_STDIN) {
      const remaining = MAX_STDIN - raw.length;
      raw += chunk.substring(0, remaining);
    }
  });

  process.stdin.on('end', () => {
    const result = run(raw);
    process.stdout.write(result);
  });
}

module.exports = { run };
