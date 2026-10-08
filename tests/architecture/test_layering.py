"""Layering rules (app_spec §4.1): api -> services -> repositories -> domain, never upward.

Two independent checks: the import-linter contracts in backend/.importlinter, and a direct AST walk
over backend/app/<layer> so a missing or weakened linter config cannot hide an upward import.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
APP_DIR = BACKEND_DIR / "app"

# Higher rank may import lower rank; importing a higher rank is an upward (forbidden) import.
LAYER_RANK: dict[str, int] = {"domain": 0, "repositories": 1, "services": 2, "api": 3}
# Extra non-rank rules: core is below every layer except domain, which must not touch it at all.
EXTRA_FORBIDDEN: dict[str, frozenset[str]] = {
    "domain": frozenset({"core"}),
    "core": frozenset({"domain", "repositories", "services", "api"}),
    "api": frozenset({"repositories"}),
}
CHECKED_LAYERS: tuple[str, ...] = ("domain", "repositories", "services", "api", "core")


@dataclass(frozen=True)
class Violation:
    location: str
    importer_layer: str
    imported: str

    def __str__(self) -> str:
        return f"{self.location}: layer '{self.importer_layer}' imports {self.imported}"


def _imported_modules(tree: ast.AST) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append((node.lineno, node.module))
    return found


def _is_forbidden(importer: str, target: str) -> bool:
    if target == importer:
        return False
    if target in EXTRA_FORBIDDEN.get(importer, frozenset()):
        return True
    if importer in LAYER_RANK and target in LAYER_RANK:
        return LAYER_RANK[target] > LAYER_RANK[importer]
    return False


def find_upward_imports(source: str, importer_layer: str, filename: str = "<memory>") -> list[Violation]:
    """Return every `app.<layer>` import in `source` that the importer's layer may not make."""
    violations: list[Violation] = []
    for lineno, module in _imported_modules(ast.parse(source, filename=filename)):
        parts = module.split(".")
        if len(parts) < 2 or parts[0] != "app":
            continue
        if _is_forbidden(importer_layer, parts[1]):
            violations.append(Violation(f"{filename}:{lineno}", importer_layer, module))
    return violations


def _lint_imports_command() -> list[str]:
    exe = shutil.which("lint-imports", path=str(Path(sys.executable).parent))
    if exe is None:
        pytest.fail("lint-imports is not installed in the test environment (poetry install --with dev)")
    return [exe, "--no-cache"]


def test_import_linter_contracts_are_kept() -> None:
    result = subprocess.run(
        _lint_imports_command(), cwd=BACKEND_DIR, capture_output=True, text=True, timeout=120, check=False
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"lint-imports failed (exit {result.returncode}):\n{output}"
    match = re.search(r"Contracts: (\d+) kept, (\d+) broken", output)
    assert match is not None, f"unexpected lint-imports output:\n{output}"
    kept, broken = int(match.group(1)), int(match.group(2))
    assert broken == 0, output
    assert kept >= 4, f"expected at least 4 layering contracts, found {kept}:\n{output}"


@pytest.mark.parametrize("layer", CHECKED_LAYERS)
def test_no_upward_imports_in_layer(layer: str) -> None:
    layer_dir = APP_DIR / layer
    assert layer_dir.is_dir(), f"missing layer package {layer_dir}"
    violations: list[Violation] = []
    for path in sorted(layer_dir.rglob("*.py")):
        rel = path.relative_to(BACKEND_DIR).as_posix()
        violations.extend(find_upward_imports(path.read_text(encoding="utf-8"), layer, rel))
    assert not violations, "upward imports found:\n" + "\n".join(str(v) for v in violations)


@pytest.mark.parametrize(
    ("layer", "bad_source"),
    [
        ("services", "from app.api.deps import require_role\n"),
        ("repositories", "from app.services import health_service\n"),
        ("domain", "import app.repositories.base\n"),
        ("domain", "from app.core.clock import Clock\n"),
        ("core", "from app.domain.money import q2\n"),
        ("api", "from app.repositories.health_repository import ping\n"),
    ],
)
def test_detector_flags_upward_import(layer: str, bad_source: str) -> None:
    """Red proof: the AST detector reports a violation for each forbidden direction."""
    violations = find_upward_imports(bad_source, layer)
    assert len(violations) == 1, f"detector missed violation in {layer}: {bad_source!r}"


@pytest.mark.parametrize(
    ("layer", "good_source"),
    [
        ("api", "from app.services.health_service import check_health\n"),
        ("services", "from app.repositories import health_repository\nfrom app.domain.money import q2\n"),
        ("repositories", "from app.domain.policy import PolicyStatus\nfrom app.core.db import DecimalText\n"),
        ("domain", "from app.domain.money import q2\nfrom decimal import Decimal\n"),
    ],
)
def test_detector_allows_downward_import(layer: str, good_source: str) -> None:
    assert find_upward_imports(good_source, layer) == []
