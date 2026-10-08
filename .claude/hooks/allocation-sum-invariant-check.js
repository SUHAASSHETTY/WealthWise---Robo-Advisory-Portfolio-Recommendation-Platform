#!/usr/bin/env node
'use strict';

// PreToolUse (Write|Edit|MultiEdit): blocks seed / migration / template / allocation files
// whose asset allocations do not sum to EXACTLY 100.00 (NFR-08, AC-02, AC-10).
// Arithmetic is done in integer hundredths — never floating point.

const path = require('path');
const { readInput, fileChange, isTestPath, lineOf, block } = require('./lib/wealthwise-hook-utils');

const HOOK = 'allocation-sum-invariant-check';
const CORE_CLASSES = ['EQUITY', 'DEBT', 'GOLD', 'CASH'];
const EXTS = new Set(['.py', '.json', '.ts', '.tsx', '.js', '.yaml', '.yml']);
const NUM = String.raw`(?:Decimal\(\s*)?["']?(-?\d+(?:\.\d+)?)["']?`;
const MAP_PAIR = new RegExp(String.raw`["']?([A-Z][A-Z_]{1,19})["']?\s*[:=]\s*` + NUM, 'g');
const ROW_PAIR = new RegExp(
  String.raw`asset_class(?:_code)?["']?\s*[:=]\s*["']([A-Z][A-Z_]{1,19})["'][^{}]*?target_pct["']?\s*[:=]\s*` + NUM,
  'g'
);

function inScope(relPath) {
  if (relPath.startsWith('.claude/') || relPath.startsWith('../') || isTestPath(relPath)) return false;
  if (!EXTS.has(path.extname(relPath).toLowerCase())) return false;
  const segs = relPath.split('/');
  const base = segs[segs.length - 1];
  return segs.some((s) => ['seed', 'seeds', 'migrations', 'fixtures'].includes(s))
    || /(template|allocation|polic)/i.test(base);
}

function toHundredths(value) {
  const m = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(value);
  if (!m) return null; // more than 2 dp, or malformed
  const cents = Number(m[2]) * 100 + Number((m[3] || '').padEnd(2, '0'));
  return m[1] === '-' ? -cents : cents;
}

function checkAllocation(pairs, where) {
  const problems = [];
  let total = 0;
  for (const [cls, raw] of pairs) {
    const cents = toHundredths(raw);
    if (cents === null) problems.push(`${where}: ${cls}=${raw} is not a 2-dp decimal`);
    else if (cents < 0 || cents > 10000) problems.push(`${where}: ${cls}=${raw} outside [0.00, 100.00]`);
    else total += cents;
  }
  if (problems.length === 0 && total !== 10000) {
    const shown = (total / 100).toFixed(2); // display only; comparison above is integer
    problems.push(`${where}: allocation {${pairs.map(([c, v]) => `${c}=${v}`).join(', ')}} sums to ${shown}, expected exactly 100.00`);
  }
  return problems;
}

function mapAllocations(text) {
  const problems = [];
  for (const block of text.matchAll(/\{[^{}]*\}/g)) {
    const pairs = [...block[0].matchAll(MAP_PAIR)].map((m) => [m[1], m[2]]);
    const core = pairs.filter(([c]) => CORE_CLASSES.includes(c)).length;
    if (core >= 3) problems.push(...checkAllocation(pairs, `line ${lineOf(text, block.index)}`));
  }
  return problems;
}

function rowAllocations(text) {
  const problems = [];
  for (const list of text.matchAll(/\[[^\[\]]*\]/g)) {
    const pairs = [...list[0].matchAll(ROW_PAIR)].map((m) => [m[1], m[2]]);
    if (pairs.length >= 2) problems.push(...checkAllocation(pairs, `line ${lineOf(text, list.index)}`));
  }
  return problems;
}

const input = readInput();
const change = input && fileChange(input);
if (!change || change.next === null || !inScope(change.relPath)) process.exit(0);

const problems = [...mapAllocations(change.next), ...rowAllocations(change.next)];
if (problems.length > 0) {
  block(HOOK, problems.map((p) => `${change.relPath} ${p}`),
    'Every allocation template/seed row must sum to exactly 100.00 with 2-dp decimal strings (recommendation_spec §2.4).');
}
process.exit(0);
