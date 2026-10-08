"""Domain purity (app_spec §4.1, backend/app/domain/CLAUDE.md): app.domain imports only stdlib and app.domain.

Independent of import-linter: a direct AST scan of every module under backend/app/domain.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
DOMAIN_DIR = BACKEND_DIR / "app" / "domain"

FORBIDDEN_ROOTS: frozenset[str] = frozenset({"fastapi", "starlette", "sqlalchemy", "pydantic", "pydantic_settings"})
FORBIDDEN_APP_PACKAGES: frozenset[str] = frozenset({"app.core", "app.api", "app.services", "app.repositories"})
STDLIB: frozenset[str] = frozenset(sys.stdlib_module_names) | {"__future__"}


def _classify(module: str) -> str | None:
    """Return a reason string if `module` may not be imported from app.domain, else None."""
    root = module.split(".")[0]
    if root in FORBIDDEN_ROOTS:
        return f"framework import '{module}'"
    if any(module == pkg or module.startswith(pkg + ".") for pkg in FORBIDDEN_APP_PACKAGES):
        return f"outer-layer import '{module}'"
    if module == "app.domain" or module.startswith("app.domain."):
        return None
    if root in STDLIB:
        return None
    return f"non-stdlib import '{module}'"


def _modules_in(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level > 0:  # relative import stays inside app.domain
            return []
        return [node.module] if node.module else []
    return []


def find_domain_import_violations(source: str, filename: str = "<memory>") -> list[str]:
    """Scan one module's source and report every forbidden import as 'file:line: reason'."""
    problems: list[str] = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        for module in _modules_in(node):
            reason = _classify(module)
            if reason is not None:
                problems.append(f"{filename}:{getattr(node, 'lineno', 0)}: {reason}")
    return problems


def _domain_files() -> list[Path]:
    files = sorted(DOMAIN_DIR.rglob("*.py"))
    assert files, f"no domain modules found under {DOMAIN_DIR}"
    return files


def test_domain_imports_only_stdlib_and_domain() -> None:
    problems: list[str] = []
    for path in _domain_files():
        rel = path.relative_to(BACKEND_DIR).as_posix()
        problems.extend(find_domain_import_violations(path.read_text(encoding="utf-8"), rel))
    assert not problems, "app.domain must stay pure:\n" + "\n".join(problems)


@pytest.mark.parametrize(
    "bad_source",
    [
        "from fastapi import APIRouter\n",
        "import starlette.responses\n",
        "from sqlalchemy.orm import Session\n",
        "from pydantic import BaseModel\n",
        "from pydantic_settings import BaseSettings\n",
        "from app.core.clock import SystemClock\n",
        "import app.api.deps\n",
        "from app.services import health_service\n",
        "from app.repositories.models.template_version import TemplateVersion\n",
        "import httpx\n",
        "def build() -> None:\n    import sqlalchemy\n",
    ],
)
def test_detector_flags_forbidden_domain_import(bad_source: str) -> None:
    """Red proof: each forbidden import in an in-memory domain module is reported."""
    problems = find_domain_import_violations(bad_source)
    assert len(problems) == 1, f"detector missed: {bad_source!r}"


@pytest.mark.parametrize(
    "good_source",
    [
        "from decimal import ROUND_HALF_EVEN, Decimal\n",
        "from collections.abc import Mapping\nimport enum\n",
        "from __future__ import annotations\n",
        "from app.domain.money import q2\n",
        "from .money import CENT\n",
    ],
)
def test_detector_allows_stdlib_and_domain_imports(good_source: str) -> None:
    assert find_domain_import_violations(good_source) == []
