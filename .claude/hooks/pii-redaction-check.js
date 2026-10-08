#!/usr/bin/env node
'use strict';

// PreToolUse (Write|Edit|MultiEdit): blocks application code that logs PII (name, email,
// PAN, phone, DOB, credentials) or financial positions (values, units, amounts, NAV, drift,
// allocation %, risk band) — NFR-03. Scope: backend/app, frontend/src, scripts (tests excluded).

const { readInput, fileChange, isTestPath, lineOf, block } = require('./lib/wealthwise-hook-utils');
const { maskCode, langOf } = require('./lib/code-mask');

const HOOK = 'pii-redaction-check';
const SCOPES = ['backend/app/', 'frontend/src/', 'scripts/'];
const LOG_CALLS = {
  py: /\b(?:logger|logging|log|LOGGER)\s*\.\s*(?:debug|info|warning|warn|error|exception|critical)\s*\(|\bprint\s*\(/g,
  js: /\b(?:console|logger|log)\s*\.\s*(?:log|debug|info|warn|error|trace)\s*\(/g,
};
const SENSITIVE = new Set([
  'name', 'full_name', 'first_name', 'last_name', 'display_name', 'username', 'user_name',
  'email', 'email_address', 'pan', 'pan_number', 'phone', 'phone_number', 'mobile',
  'dob', 'date_of_birth', 'address', 'password', 'token', 'access_token', 'salary', 'income',
  'units', 'quantity', 'value', 'current_value', 'total_value', 'target_value', 'trade_value',
  'target_amount', 'amount', 'nav', 'balance', 'holding', 'holdings', 'position', 'positions',
  'drift', 'drift_pct', 'target_pct', 'current_pct', 'percent_complete', 'post_trade_cash',
  'risk_band', 'band', 'assigned_band', 'answers',
]);
const LITERALS = [
  ['email address literal', /[\w.+-]+@[\w-]+\.[\w.]+/],
  ['PAN literal', /\b[A-Z]{5}[0-9]{4}[A-Z]\b/],
  ['phone number literal', /(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)/],
];

function snake(token) {
  return token.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();
}

function callEnd(masked, openIdx) {
  let depth = 0;
  for (let i = openIdx; i < masked.length; i += 1) {
    if (masked[i] === '(') depth += 1;
    if (masked[i] === ')') depth -= 1;
    if (depth === 0) return i + 1;
  }
  return masked.length;
}

function sensitiveTokens(maskedCall, rawCall) {
  const code = maskedCall.replace(/\blen\s*\(\s*[\w.]+\s*\)|\.length\b/g, ' ');
  const idents = (code.match(/[A-Za-z_]\w*/g) || []).map(snake);
  const keys = [...rawCall.matchAll(/["'](\w+)["']\s*:/g)].map((m) => snake(m[1]));
  const found = new Set([...idents, ...keys].filter((t) => SENSITIVE.has(t)));
  for (const [label, re] of LITERALS) if (re.test(rawCall)) found.add(label);
  return [...found];
}

function findViolations(text, lang) {
  const masked = maskCode(text, lang);
  const problems = [];
  for (const m of masked.matchAll(LOG_CALLS[lang])) {
    const end = callEnd(masked, m.index + m[0].length - 1);
    const hits = sensitiveTokens(masked.slice(m.index, end), text.slice(m.index, end));
    if (hits.length > 0) {
      problems.push(`line ${lineOf(text, m.index)}: log/print call references ${hits.join(', ')}`);
    }
  }
  return problems;
}

const input = readInput();
const change = input && fileChange(input);
if (!change || change.next === null) process.exit(0);
const lang = langOf(change.relPath);
const inScope = SCOPES.some((s) => change.relPath.startsWith(s)) && !isTestPath(change.relPath);
if (!lang || !inScope) process.exit(0);

const problems = findViolations(change.next, lang);
if (problems.length > 0) {
  block(HOOK, problems.map((p) => `${change.relPath} ${p}`),
    'Log only IDs, enums, counts and durations via extra={...} allow-listed keys (app_spec §5.6, NFR-03).');
}
process.exit(0);
