"""AC coverage report: maps every AC-NN in the specs to the tests that reference it.

Usage:
    python3 scripts/ac_coverage.py            # table, exit 1 if any AC has no test
    python3 scripts/ac_coverage.py --strict   # also require every AC-NN.k scenario to be cited
    python3 scripts/ac_coverage.py --json     # machine-readable output (used by agent_sdk_review.py)

Recognised test references:
    pytest      @pytest.mark.ac("AC-NN") on a test function; scenario IDs AC-NN.k cited anywhere in the file
    Playwright  test('AC-NN: …') titles in frontend/e2e/**/*.spec.ts
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AC_MAP_ROW = re.compile(r"^\| (AC-\d{2}) \|", re.MULTILINE)
SCENARIO = re.compile(r"\*\*(AC-\d{2}\.\d+) ")
PY_SCENARIO_CITE = re.compile(r"\b(AC-\d{2}\.\d+)\b")
TS_TITLE = re.compile(r"\btest\(\s*[\"'`](AC-\d{2}):")


@dataclass
class AcCoverage:
    ac_id: str
    scenarios: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    cited_scenarios: set[str] = field(default_factory=set)

    @property
    def uncited(self) -> list[str]:
        return [s for s in self.scenarios if s not in self.cited_scenarios]


def load_acs(specs_dir: Path) -> dict[str, AcCoverage]:
    app_spec = (specs_dir / "app_spec.md").read_text(encoding="utf-8")
    acs = {ac: AcCoverage(ac) for ac in dict.fromkeys(AC_MAP_ROW.findall(app_spec))}
    for spec in sorted(specs_dir.glob("*_spec.md")):
        for scenario in SCENARIO.findall(spec.read_text(encoding="utf-8")):
            parent = scenario.split(".")[0]
            if parent in acs and scenario not in acs[parent].scenarios:
                acs[parent].scenarios.append(scenario)
    return acs


def ac_markers(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """AC ids from `@pytest.mark.ac("AC-NN")` decorators, wherever they sit among other decorators."""
    ids: list[str] = []
    for deco in func.decorator_list:
        if (
            isinstance(deco, ast.Call)
            and isinstance(deco.func, ast.Attribute)
            and deco.func.attr == "ac"
            and deco.args
            and isinstance(deco.args[0], ast.Constant)
            and isinstance(deco.args[0].value, str)
        ):
            ids.append(deco.args[0].value)
    return ids


def scan_python_tests(tests_dir: Path, acs: dict[str, AcCoverage]) -> None:
    for path in sorted(tests_dir.rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(tests_dir.parent).as_posix()
        for node in ast.walk(ast.parse(text, filename=str(path))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                for ac_id in ac_markers(node):
                    if ac_id in acs:
                        acs[ac_id].tests.append(f"{rel}::{node.name}")
        for scenario in PY_SCENARIO_CITE.findall(text):
            parent = scenario.split(".")[0]
            if parent in acs:
                acs[parent].cited_scenarios.add(scenario)


def scan_playwright_tests(e2e_dir: Path, acs: dict[str, AcCoverage]) -> None:
    for path in sorted(e2e_dir.rglob("*.spec.ts")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(e2e_dir.parent.parent).as_posix()
        for ac_id in TS_TITLE.findall(text):
            if ac_id in acs:
                acs[ac_id].tests.append(f"{rel} (playwright)")


def build_report(root: Path) -> dict[str, AcCoverage]:
    acs = load_acs(root / "specs")
    if (root / "tests").is_dir():
        scan_python_tests(root / "tests", acs)
    if (root / "frontend" / "e2e").is_dir():
        scan_playwright_tests(root / "frontend" / "e2e", acs)
    return acs


def print_table(acs: dict[str, AcCoverage], strict: bool) -> None:
    print(f"{'AC':<7} {'scenarios':>9} {'tests':>6}  status")
    for cov in acs.values():
        ok = bool(cov.tests) and (not strict or not cov.uncited)
        print(f"{cov.ac_id:<7} {len(cov.scenarios):>9} {len(cov.tests):>6}  {'OK' if ok else 'MISSING'}")
        for test_ref in cov.tests:
            print(f"        - {test_ref}")
        if strict and cov.uncited:
            print(f"        uncited scenarios: {', '.join(cov.uncited)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true", help="require every AC-NN.k to be cited")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    parser.add_argument("--root", type=Path, default=ROOT, help="project root (default: repo root)")
    args = parser.parse_args(argv)

    acs = build_report(args.root.resolve())
    failing = [c.ac_id for c in acs.values() if not c.tests or (args.strict and c.uncited)]
    if args.json:
        payload = {
            c.ac_id: {"scenarios": c.scenarios, "tests": c.tests, "uncited": c.uncited}
            for c in acs.values()
        }
        print(json.dumps({"acs": payload, "failing": failing}, indent=2))
    else:
        print_table(acs, args.strict)
        print(f"\nRESULT: {'PASS' if not failing else 'FAIL'} "
              f"({len(acs) - len(failing)}/{len(acs)} ACs covered)")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
