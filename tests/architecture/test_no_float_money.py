"""NFR-01 (app_spec §5.1): money, percent, units and NAV are Decimal, never float.

AST scan of backend/app/{domain,services,repositories}: fails on any `float` name (annotation, call,
isinstance target), any float literal (which also covers `Decimal(0.1)`), and any SQLAlchemy
`Float`/`Numeric`/`REAL`/`DOUBLE` column type (SQLite stores NUMERIC as binary REAL).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
SCANNED_PACKAGES: tuple[str, ...] = ("domain", "services", "repositories")
FLOAT_SQL_TYPES: frozenset[str] = frozenset({"Float", "Numeric", "NUMERIC", "REAL", "DOUBLE", "Double", "FLOAT"})


def _node_problem(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name) and node.id == "float":
        return "uses builtin 'float'"
    if isinstance(node, ast.Constant) and isinstance(node.value, float):
        return f"float literal {node.value!r}"
    if isinstance(node, ast.Name) and node.id in FLOAT_SQL_TYPES:
        return f"SQLAlchemy float-backed type '{node.id}'"
    if isinstance(node, ast.Attribute) and node.attr in FLOAT_SQL_TYPES:
        return f"SQLAlchemy float-backed type '.{node.attr}'"
    if isinstance(node, ast.alias) and node.name.split(".")[-1] in FLOAT_SQL_TYPES:
        return f"imports float-backed type '{node.name}'"
    return None


def find_float_money(source: str, filename: str = "<memory>") -> list[str]:
    """Return 'file:line: reason' for every float usage in `source`."""
    problems: list[str] = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        if isinstance(node, ast.Import | ast.ImportFrom):
            problems.extend(
                f"{filename}:{node.lineno}: {reason}"
                for alias in node.names
                if (reason := _node_problem(alias)) is not None
            )
            continue
        reason = _node_problem(node)
        if reason is not None:
            problems.append(f"{filename}:{getattr(node, 'lineno', 0)}: {reason}")
    return problems


def _scanned_files() -> list[Path]:
    files = [p for pkg in SCANNED_PACKAGES for p in sorted((BACKEND_DIR / "app" / pkg).rglob("*.py"))]
    assert files, "no modules found to scan"
    return files


def test_no_float_in_money_layers() -> None:
    problems: list[str] = []
    for path in _scanned_files():
        rel = path.relative_to(BACKEND_DIR).as_posix()
        problems.extend(find_float_money(path.read_text(encoding="utf-8"), rel))
    assert not problems, "float found in money code (NFR-01):\n" + "\n".join(problems)


@pytest.mark.parametrize(
    "bad_source",
    [
        "x: float = 0\n",
        "def nav() -> float:\n    return 0\n",
        "units = float('12.5')\n",
        "drift_threshold = 5.0\n",
        "from decimal import Decimal\nprice = Decimal(101.25)\n",
        "from sqlalchemy import Float\n",
        "import sqlalchemy as sa\namount = sa.Numeric(12, 2)\n",
        "from sqlalchemy.types import REAL\n",
    ],
)
def test_detector_flags_float_money(bad_source: str) -> None:
    """Red proof: each float form in an in-memory module is reported with a line number."""
    problems = find_float_money(bad_source)
    assert problems, f"detector missed float usage in {bad_source!r}"
    assert all(p.startswith("<memory>:") for p in problems)


def test_detector_reports_file_and_line() -> None:
    source = 'from decimal import Decimal\n\nCENT = Decimal("0.01")\nratio: float = 0.25\n'
    problems = find_float_money(source, "app/domain/sample.py")
    assert "app/domain/sample.py:4: uses builtin 'float'" in problems
    assert "app/domain/sample.py:4: float literal 0.25" in problems


@pytest.mark.parametrize(
    "good_source",
    [
        'from decimal import Decimal\nCENT = Decimal("0.01")\n',
        "count: int = 3\n",
        "from sqlalchemy import String\nfrom app.core.db import DecimalText\n",
    ],
)
def test_detector_allows_decimal_from_str(good_source: str) -> None:
    assert find_float_money(good_source) == []
