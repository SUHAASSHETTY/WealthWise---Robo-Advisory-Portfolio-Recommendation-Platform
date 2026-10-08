"""Spec-vs-code AC coverage review using the Claude Agent SDK.

Writes specs/reviews/sdk-review-<YYYY-MM-DD>.md with:
  1. a deterministic AC → test traceability table (scripts/ac_coverage.py), and
  2. a read-only agent review (Read/Grep/Glob only) of whether each AC's tests actually
     assert the spec's Then-clauses and whether implementing code exists.

Usage:
    python3 scripts/agent_sdk_review.py                 # full review (needs claude-agent-sdk + Claude auth)
    python3 scripts/agent_sdk_review.py --offline       # deterministic section only, no API call
    python3 scripts/agent_sdk_review.py --model claude-opus-5-5 --max-turns 40 --max-budget-usd 3

Requires: pip install claude-agent-sdk (only for the agent review).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ac_coverage import ROOT, AcCoverage, build_report  # noqa: E402

DEFAULT_MODEL = "claude-opus-5-5"
READ_ONLY_TOOLS = ["Read", "Grep", "Glob"]
BLOCKED_TOOLS = ["Write", "Edit", "MultiEdit", "Bash", "WebFetch", "WebSearch", "NotebookEdit", "Task"]
SENSITIVE_PARTS = (".git", ".env", "id_rsa", "id_ed25519")
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12")

SYSTEM_PROMPT = """You are a skeptical spec-conformance reviewer for the WealthWise repository.
You may only read files. specs/*.md are the source of truth (Spec-Is-Truth).
For each acceptance criterion you are given, open its owning spec section and the listed tests,
then judge whether the tests assert every value in each scenario's Then-clause, and whether
production code implementing it exists under backend/app or frontend/src.
Never invent files or test results; cite file paths (and line numbers where possible).
Do not include customer PII or real data in your output."""

REVIEW_INSTRUCTIONS = """Review AC coverage for this repository.

Deterministic traceability scan (from scripts/ac_coverage.py):
```json
{coverage_json}
```

Produce Markdown with exactly these sections:
## Verdict
One line: `VERDICT: PASS` only if every AC has tests that assert its scenarios and implementing code exists; otherwise `VERDICT: FAIL`.
## Per-AC findings
A table: AC | spec scenarios | tests found | Then-clauses asserted? (yes/partial/no) | implementation found? | notes (cite paths).
## Gaps (highest risk first)
Numbered list of concrete missing tests or code, each with the spec scenario ID (AC-NN.k) and the file it belongs in.
Output only the Markdown, no preamble."""


def is_safe_repo_path(raw: str | None) -> bool:
    """True only for paths inside the repo that are not secrets, keys or git internals."""
    target = (ROOT / (raw or ".")).resolve()
    if target != ROOT and ROOT not in target.parents:
        return False
    rel_parts = target.relative_to(ROOT).parts
    if any(part.startswith(SENSITIVE_PARTS) for part in rel_parts):
        return False
    return not target.name.endswith(SENSITIVE_SUFFIXES)


async def gate_tool(tool_name: str, input_data: dict, context: object) -> object:
    """Every tool call is routed here: allow only Read/Grep/Glob on safe in-repo paths."""
    from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

    if tool_name not in READ_ONLY_TOOLS:
        return PermissionResultDeny(message=f"{tool_name} is not permitted in this read-only review")
    raw_path = input_data.get("file_path") if tool_name == "Read" else input_data.get("path")
    if not is_safe_repo_path(raw_path):
        return PermissionResultDeny(message="path is outside the repository or is a protected file")
    return PermissionResultAllow(updated_input=input_data)


def coverage_payload(acs: dict[str, AcCoverage]) -> dict[str, object]:
    return {
        ac_id: {"scenarios": cov.scenarios, "tests": cov.tests, "uncited": cov.uncited}
        for ac_id, cov in acs.items()
    }


def deterministic_section(acs: dict[str, AcCoverage]) -> str:
    rows = ["| AC | Scenarios | Tests | Status | Test references |", "|---|---|---|---|---|"]
    for cov in acs.values():
        refs = "<br>".join(f"`{t}`" for t in cov.tests) or "—"
        status = "OK" if cov.tests else "MISSING"
        rows.append(f"| {cov.ac_id} | {len(cov.scenarios)} | {len(cov.tests)} | {status} | {refs} |")
    covered = sum(1 for c in acs.values() if c.tests)
    rows.append(f"\n**Traceability:** {covered}/{len(acs)} ACs have at least one tagged test.")
    return "\n".join(rows)


async def run_agent_review(acs: dict[str, AcCoverage], args: argparse.Namespace) -> tuple[str, str]:
    from claude_agent_sdk import ClaudeAgentOptions, query
    from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock

    # No allowed_tools: allow rules would approve calls before can_use_tool runs.
    # setting_sources=[] keeps project/user settings (e.g. Harness `git push` allow rules) out.
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        can_use_tool=gate_tool,
        disallowed_tools=BLOCKED_TOOLS,
        setting_sources=[],
        mcp_servers={},
        permission_mode="default",
        cwd=str(ROOT),
        max_turns=args.max_turns,
        max_budget_usd=args.max_budget_usd,
        model=args.model,
    )
    prompt = REVIEW_INSTRUCTIONS.format(coverage_json=json.dumps(coverage_payload(acs), indent=2))
    texts: list[str] = []
    final: str | None = None
    meta = "agent review did not return a result message"
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            texts.extend(block.text for block in message.content if isinstance(block, TextBlock))
        elif isinstance(message, ResultMessage):
            final = message.result
            meta = (f"subtype={message.subtype}, is_error={message.is_error}, turns={message.num_turns}, "
                    f"cost_usd={message.total_cost_usd}")
    body = final or (texts[-1] if texts else "_The agent returned no text._")
    return body, meta


def render_report(acs: dict[str, AcCoverage], agent_body: str, agent_meta: str, args: argparse.Namespace) -> str:
    return "\n\n".join([
        f"# SDK spec-vs-code review — {args.date}",
        f"Generated by `scripts/agent_sdk_review.py` (Claude Agent SDK, model `{args.model}`, "
        f"tools {', '.join(READ_ONLY_TOOLS)} only, repo-confined).",
        "## Deterministic AC traceability",
        deterministic_section(acs),
        "## Agent review",
        f"_Run metadata: {agent_meta}_",
        agent_body,
    ]) + "\n"


def iso_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--date must be YYYY-MM-DD, got {value!r}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spec-vs-code AC coverage review (Claude Agent SDK).")
    parser.add_argument("--offline", action="store_true", help="skip the agent review (no API call)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-turns", type=int, default=40)
    parser.add_argument("--max-budget-usd", type=float, default=3.0)
    parser.add_argument("--date", type=iso_date, default=date.today().isoformat(), help="report date (YYYY-MM-DD)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    acs = build_report(ROOT)
    if args.offline:
        agent_body, agent_meta = "_Skipped: run with network and claude-agent-sdk to include the agent review._", "offline"
    else:
        try:
            agent_body, agent_meta = asyncio.run(run_agent_review(acs, args))
        except ImportError:
            sys.stderr.write("claude-agent-sdk is not installed: pip install claude-agent-sdk (or use --offline)\n")
            return 2
    report_path = ROOT / "specs" / "reviews" / f"sdk-review-{args.date}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(acs, agent_body, agent_meta, args), encoding="utf-8")
    print(f"Wrote {report_path.relative_to(ROOT)} ({agent_meta})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
