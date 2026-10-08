#!/usr/bin/env node
'use strict';

// Runs each WealthWise project hook against passing and failing inputs.
// Usage: node .claude/hooks/tests/run-wealthwise-hook-tests.js
// Builds a throwaway fixture project in the OS temp dir (locked migration + published template).

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const HOOKS_DIR = path.resolve(__dirname, '..');
const FIX = fs.mkdtempSync(path.join(os.tmpdir(), 'ww-hooks-'));

const TEMPLATE_OK = JSON.stringify({ templates: {
  CONSERVATIVE: { EQUITY: '20.00', DEBT: '60.00', GOLD: '10.00', CASH: '10.00' },
  MODERATE: { EQUITY: '50.00', DEBT: '35.00', GOLD: '10.00', CASH: '5.00' },
  AGGRESSIVE: { EQUITY: '75.00', DEBT: '15.00', GOLD: '7.50', CASH: '2.50' },
}, drift_threshold_pct: '5.00' }, null, 2);
const TEMPLATE_BAD = TEMPLATE_OK.replace('"GOLD": "7.50"', '"GOLD": "7.51"');
const MANUAL_ROWS_BAD = [
  'MANUAL_RECOMMENDATION = [',
  '    {"asset_class": "EQUITY", "target_pct": Decimal("40.00")},',
  '    {"asset_class": "DEBT", "target_pct": Decimal("40.00")},',
  '    {"asset_class": "GOLD", "target_pct": Decimal("10.00")},',
  '    {"asset_class": "CASH", "target_pct": Decimal("9.99")},',
  ']',
].join('\n');
const PY_LOG_OK = [
  'logger.info(',
  '    "holdings fetched",',
  '    extra={"customer_id": str(customer_id), "line_count": len(holdings)},',
  ')',
].join('\n');
const PY_LOG_BAD = 'logger.info("login ok", extra={"email": customer.email, "customer_id": cid})';
const PY_PRINT_BAD = 'print(f"Welcome {customer.full_name}, PAN ABCDE1234F")';
const TS_LOG_BAD = 'console.log(`holding value ${holding.currentValue}`);';
const DOMAIN_OK = [
  'from decimal import Decimal, ROUND_HALF_EVEN',
  '',
  'CENT = Decimal("0.01")  # not 0.01 float',
  'def q2(x: Decimal) -> Decimal:',
  '    """Quantise e.g. 12.345 -> 12.34."""',
  '    return x.quantize(CENT, rounding=ROUND_HALF_EVEN)',
].join('\n');
const DOMAIN_BAD = [
  'def drift(current: float, target: float) -> float:',
  '    return abs(current - target) * 1.0',
].join('\n');

function writeFixture(rel, content) {
  const abs = path.join(FIX, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, content);
}

function withStatus(status) {
  return JSON.stringify(Object.assign({ status }, JSON.parse(TEMPLATE_OK)), null, 2);
}

function setupFixture() {
  writeFixture('backend/migrations/versions/0001_seed_policy_v1.py', '"""v1 seed"""\n');
  writeFixture('backend/migrations/LOCKED_HASHES.txt', 'abc123  0001_seed_policy_v1.py\n');
  writeFixture('backend/app/seed/policies/template_v1.json', withStatus('PUBLISHED'));
  writeFixture('backend/app/seed/policies/template_v2_draft.json', withStatus('DRAFT'));
}

function write(rel, content) {
  return { tool_name: 'Write', cwd: FIX, tool_input: { file_path: path.join(FIX, rel), content } };
}
function edit(rel, oldStr, newStr) {
  return { tool_name: 'Edit', cwd: FIX, tool_input: { file_path: path.join(FIX, rel), old_string: oldStr, new_string: newStr } };
}
function bash(command) {
  return { tool_name: 'Bash', cwd: FIX, tool_input: { command } };
}

const CASES = [
  ['allocation-sum-invariant-check', 'PASS', 'template JSON, every band = 100.00', write('backend/app/seed/policies/template_v2.json', TEMPLATE_OK)],
  ['allocation-sum-invariant-check', 'BLOCK', 'template JSON, AGGRESSIVE = 100.01', write('backend/app/seed/policies/template_v2.json', TEMPLATE_BAD)],
  ['allocation-sum-invariant-check', 'BLOCK', 'seed rows (Python), manual allocation = 99.99', write('backend/app/seed/manual_allocations.py', MANUAL_ROWS_BAD)],
  ['allocation-sum-invariant-check', 'PASS', 'out of scope: test file with a deliberately bad sum', write('tests/unit/domain/allocation/test_templates.py', MANUAL_ROWS_BAD)],
  ['template-immutability-check', 'PASS', 'new migration file (not locked)', write('backend/migrations/versions/0002_template_v2.py', '"""v2"""\n')],
  ['template-immutability-check', 'BLOCK', 'edit locked migration 0001', edit('backend/migrations/versions/0001_seed_policy_v1.py', 'v1 seed', 'v1 seed changed')],
  ['template-immutability-check', 'BLOCK', 'edit PUBLISHED template_v1.json', edit('backend/app/seed/policies/template_v1.json', '"7.50"', '"8.50"')],
  ['template-immutability-check', 'PASS', 'edit DRAFT template_v2_draft.json', edit('backend/app/seed/policies/template_v2_draft.json', '"7.50"', '"8.50"')],
  ['template-immutability-check', 'BLOCK', 'Bash: UPDATE template_versions', bash(`sqlite3 wealthwise.db "UPDATE template_versions SET definition='{}' WHERE version_no=1"`)],
  ['template-immutability-check', 'BLOCK', 'Bash: rm locked migration', bash('rm backend/migrations/versions/0001_seed_policy_v1.py')],
  ['template-immutability-check', 'PASS', 'Bash: SELECT from template_versions', bash('sqlite3 wealthwise.db "SELECT version_no, status FROM template_versions"')],
  ['pii-redaction-check', 'PASS', 'service logs IDs and a count only', write('backend/app/services/holdings_service.py', PY_LOG_OK)],
  ['pii-redaction-check', 'BLOCK', 'logger.info with email in extra', write('backend/app/services/auth_service.py', PY_LOG_BAD)],
  ['pii-redaction-check', 'BLOCK', 'print of full_name + PAN literal', write('scripts/seed_report.py', PY_PRINT_BAD)],
  ['pii-redaction-check', 'BLOCK', 'TS console.log of position value', write('frontend/src/features/holdings/HoldingsTable.tsx', TS_LOG_BAD)],
  ['no-float-money-check', 'PASS', 'Decimal("0.01") with float-looking text only in strings/comments', write('backend/app/domain/money.py', DOMAIN_OK)],
  ['no-float-money-check', 'BLOCK', 'float annotations + float literal in domain', write('backend/app/domain/portfolio/drift.py', DOMAIN_BAD)],
  ['no-float-money-check', 'PASS', 'out of scope: api layer file', write('backend/app/api/schemas/holdings.py', DOMAIN_BAD)],
];

function runCase([hook, expected, label, input]) {
  const r = spawnSync('node', [path.join(HOOKS_DIR, `${hook}.js`)], { input: JSON.stringify(input), encoding: 'utf8' });
  const actual = r.status === 2 ? 'BLOCK' : r.status === 0 ? 'PASS' : `ERROR(${r.status})`;
  const ok = actual === expected;
  console.log(`[${ok ? 'OK  ' : 'FAIL'}] ${hook} | ${label} | expected ${expected}, got ${actual} (exit ${r.status})`);
  if (r.stderr.trim()) console.log(r.stderr.trimEnd().split('\n').map((l) => `       ${l}`).join('\n'));
  return ok;
}

setupFixture();
const results = CASES.map(runCase);
const passed = results.filter(Boolean).length;
console.log(`\nRESULT: ${passed}/${results.length} cases behaved as expected`);
fs.rmSync(FIX, { recursive: true, force: true });
process.exit(passed === results.length ? 0 : 1);
