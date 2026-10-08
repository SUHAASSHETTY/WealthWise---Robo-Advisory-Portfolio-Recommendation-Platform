#!/usr/bin/env node
'use strict';

// PreToolUse (Write|Edit|MultiEdit|Bash): blocks
//   1. edits/overwrites of locked migrations (listed in backend/migrations/LOCKED_HASHES.txt)
//   2. edits/overwrites of existing policy/template definition files whose status is PUBLISHED
//   3. Bash commands that UPDATE/DELETE published policy tables or rm/mv/sed -i a locked migration
// (admin_versioning_spec §2.1, NFR-05, NFR-08, AC-10)

const path = require('path');
const { readInput, projectRoot, readIfExists, fileChange, isTestPath, block } = require('./lib/wealthwise-hook-utils');

const HOOK = 'template-immutability-check';
const LOCK_FILE = 'backend/migrations/LOCKED_HASHES.txt';
const PUBLISHED = /["']?status["']?\s*[:=]\s*["']PUBLISHED["']/;
const POLICY_TABLE_MUTATION = /\b(UPDATE|DELETE\s+FROM)\s+["'`]?(template_versions|risk_policy_versions)\b/i;
const FILE_MUTATION = /(\brm\b|\bmv\b|\bsed\s+-i|\btruncate\b|\btee\b|>)/;

function lockedMigrations(input) {
  const text = readIfExists(path.join(projectRoot(input), LOCK_FILE)) || '';
  return text.split('\n')
    .map((line) => line.trim().split(/\s+/).pop())
    .filter((name) => name && name.endsWith('.py'));
}

function isPolicyDefinition(relPath) {
  const segs = relPath.split('/');
  return segs.some((s) => ['seed', 'seeds', 'migrations'].includes(s))
    || /(template|polic)/i.test(segs[segs.length - 1]);
}

function checkFileChange(input) {
  const change = fileChange(input);
  if (!change || change.current === null || isTestPath(change.relPath)) return [];
  const problems = [];
  const base = path.basename(change.relPath);
  if (change.relPath.startsWith('backend/migrations/') && lockedMigrations(input).includes(base)) {
    problems.push(`${change.relPath} is a locked migration from an approved phase — migrations are append-only`);
  }
  if (isPolicyDefinition(change.relPath) && PUBLISHED.test(change.current)) {
    problems.push(`${change.relPath} contains a PUBLISHED policy/template version — published versions are immutable`);
  }
  return problems;
}

function checkBash(input) {
  const command = (input.tool_input && input.tool_input.command) || '';
  const problems = [];
  if (POLICY_TABLE_MUTATION.test(command)) {
    problems.push('command mutates template_versions / risk_policy_versions directly');
  }
  const touched = lockedMigrations(input).filter((name) => command.includes(name));
  if (touched.length > 0 && FILE_MUTATION.test(command)) {
    problems.push(`command modifies locked migration(s): ${touched.join(', ')}`);
  }
  return problems;
}

const input = readInput();
if (!input) process.exit(0);
const problems = input.tool_name === 'Bash' ? checkBash(input) : checkFileChange(input);
if (problems.length > 0) {
  block(HOOK, problems,
    'Create a NEW version (draft → publish) or a NEW Alembic revision instead; see /publish-template-version.');
}
process.exit(0);
