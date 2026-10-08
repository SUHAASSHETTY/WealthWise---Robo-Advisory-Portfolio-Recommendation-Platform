'use strict';

// Shared helpers for the WealthWise project hooks.
// Unlike the Harness hooks, block messages go to STDERR with exit code 2,
// which is what Claude Code feeds back to the agent for PreToolUse hooks.

const fs = require('fs');
const path = require('path');

function readInput() {
  try {
    return JSON.parse(fs.readFileSync(0, 'utf8'));
  } catch (_) {
    return null;
  }
}

function projectRoot(input) {
  return (input && input.cwd) || process.cwd();
}

function toRelative(input, filePath) {
  const root = projectRoot(input);
  const abs = path.resolve(root, filePath);
  return path.relative(root, abs).split(path.sep).join('/');
}

function readIfExists(absPath) {
  try {
    return fs.readFileSync(absPath, 'utf8');
  } catch (_) {
    return null;
  }
}

function applyEdit(text, oldStr, newStr, replaceAll) {
  if (text === null) return null;
  if (replaceAll) return text.split(oldStr).join(newStr);
  const idx = text.indexOf(oldStr);
  if (idx === -1) return null;
  return text.slice(0, idx) + newStr + text.slice(idx + oldStr.length);
}

// Returns { relPath, absPath, current, next } for Write/Edit/MultiEdit, else null.
function fileChange(input) {
  const ti = (input && input.tool_input) || {};
  if (!ti.file_path) return null;
  const absPath = path.resolve(projectRoot(input), ti.file_path);
  const current = readIfExists(absPath);
  let next = null;
  if (input.tool_name === 'Write') next = ti.content || '';
  if (input.tool_name === 'Edit') {
    next = applyEdit(current, ti.old_string || '', ti.new_string || '', Boolean(ti.replace_all));
  }
  if (input.tool_name === 'MultiEdit' && Array.isArray(ti.edits)) {
    next = ti.edits.reduce(
      (acc, e) => applyEdit(acc, e.old_string || '', e.new_string || '', Boolean(e.replace_all)),
      current
    );
  }
  return { relPath: toRelative(input, ti.file_path), absPath, current, next };
}

function isTestPath(relPath) {
  return relPath.split('/').some((seg) => ['tests', 'test', '__tests__', 'e2e'].includes(seg))
    || /(^|\/)test_[^/]*\.py$/.test(relPath) || /\.(test|spec)\.[jt]sx?$/.test(relPath);
}

function lineOf(text, index) {
  return text.slice(0, index).split('\n').length;
}

function block(hookName, violations, fix) {
  const lines = [`BLOCKED by ${hookName}:`]
    .concat(violations.map((v) => `  - ${v}`))
    .concat(fix ? [`Fix: ${fix}`] : []);
  process.stderr.write(lines.join('\n') + '\n');
  process.exit(2);
}

module.exports = {
  readInput, projectRoot, toRelative, readIfExists, fileChange, isTestPath, lineOf, block,
};
