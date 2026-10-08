#!/usr/bin/env node
'use strict';

// PreToolUse (Write|Edit|MultiEdit): flags and blocks floating-point usage in money code —
// backend/app/domain/** and backend/app/services/** (NFR-01). Strings and comments are
// masked first, so Decimal("0.01") and docstrings are fine; 0.01, float(x), `: float`,
// SQLAlchemy Float and exponent literals are not.

const { readInput, fileChange, isTestPath, lineOf, block } = require('./lib/wealthwise-hook-utils');
const { maskCode } = require('./lib/code-mask');

const HOOK = 'no-float-money-check';
const SCOPES = ['backend/app/domain/', 'backend/app/services/'];
const RULES = [
  ['`float` type or float() conversion', /\bfloat\b/g],
  ['SQLAlchemy Float column', /\bFloat\b/g],
  ['float literal', /(?<![\w.])\d+\.\d*(?:[eE][-+]?\d+)?(?![\w.])|(?<![\w.])\.\d+(?![\w.])/g],
  ['exponent (float) literal', /(?<![\w.])\d+[eE][-+]?\d+(?![\w.])/g],
];

function findViolations(text) {
  const masked = maskCode(text, 'py');
  const lines = text.split('\n');
  const problems = [];
  for (const [label, re] of RULES) {
    for (const m of masked.matchAll(re)) {
      const line = lineOf(text, m.index);
      problems.push(`line ${line}: ${label} → ${lines[line - 1].trim()}`);
    }
  }
  return problems;
}

const input = readInput();
const change = input && fileChange(input);
if (!change || change.next === null) process.exit(0);
const inScope = change.relPath.endsWith('.py')
  && SCOPES.some((s) => change.relPath.startsWith(s))
  && !isTestPath(change.relPath);
if (!inScope) process.exit(0);

const problems = findViolations(change.next);
if (problems.length > 0) {
  block(HOOK, problems.map((p) => `${change.relPath} ${p}`),
    'Use decimal.Decimal built from str/int and quantize per app_spec §5.1 (NFR-01). Never float.');
}
process.exit(0);
