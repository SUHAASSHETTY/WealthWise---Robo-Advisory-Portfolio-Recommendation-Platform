"""Literal policy definitions from the specs, shared by tests. Never computed — copied from the spec text."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

SEED_DIR = Path(__file__).resolve().parents[2] / "backend" / "app" / "seed"

V1_TEMPLATES: dict[str, dict[str, str]] = {
    "CONSERVATIVE": {"EQUITY": "20.00", "DEBT": "60.00", "GOLD": "10.00", "CASH": "10.00"},
    "MODERATE": {"EQUITY": "50.00", "DEBT": "35.00", "GOLD": "10.00", "CASH": "5.00"},
    "AGGRESSIVE": {"EQUITY": "75.00", "DEBT": "15.00", "GOLD": "7.50", "CASH": "2.50"},
}
V1_HORIZON_RULES: list[dict[str, Any]] = [
    {"code": "H_84_PLUS", "min_months": 84, "max_months": None, "shift": "0.00", "from": "EQUITY", "to": "DEBT"},
    {"code": "H_60_83", "min_months": 60, "max_months": 83, "shift": "10.00", "from": "EQUITY", "to": "DEBT"},
    {"code": "H_36_59", "min_months": 36, "max_months": 59, "shift": "20.00", "from": "EQUITY", "to": "DEBT"},
    {"code": "H_12_35", "min_months": 12, "max_months": 35, "shift": "30.00", "from": "EQUITY", "to": "DEBT"},
    {"code": "H_0_11", "min_months": 0, "max_months": 11, "shift": "ALL", "from": "EQUITY", "to": "CASH"},
]
TEMPLATE_V1: dict[str, Any] = {
    "templates": V1_TEMPLATES,
    "horizon_rules": V1_HORIZON_RULES,
    "drift_threshold_pct": "5.00",
}
ASSET_CLASSES = ("EQUITY", "DEBT", "GOLD", "CASH")

V1_BANDS: list[dict[str, Any]] = [
    {"band": "CONSERVATIVE", "min_score": 0, "max_score": 11},
    {"band": "MODERATE", "min_score": 12, "max_score": 20},
    {"band": "AGGRESSIVE", "min_score": 21, "max_score": 28},
]
V1_POINTS: dict[str, dict[str, int]] = {
    "AGE": {"AGE_18_29": 4, "AGE_30_39": 3, "AGE_40_49": 2, "AGE_50_59": 1, "AGE_60_PLUS": 0},
    "HORIZON": {"LT_3Y": 0, "Y3_5": 1, "Y5_7": 2, "Y7_10": 3, "GT_10Y": 4},
    "INCOME_STABILITY": {
        "NO_REGULAR": 0,
        "IRREGULAR": 1,
        "STABLE_SINGLE": 2,
        "STABLE_GROWING": 3,
        "MULTIPLE_STABLE": 4,
    },
    "EMERGENCY_FUND": {"NONE": 0, "LT_3M": 1, "M3_6": 2, "M6_12": 3, "GT_12M": 4},
    "LOSS_REACTION": {"SELL_ALL": 0, "SELL_SOME": 1, "HOLD": 2, "BUY_SOME": 3, "BUY_MORE": 4},
    "EXPERIENCE": {"NONE": 0, "DEPOSITS_ONLY": 1, "FUNDS_LT_3Y": 2, "FUNDS_STOCKS_3_7Y": 3, "ACTIVE_GT_7Y": 4},
    "OBJECTIVE": {"PRESERVE": 0, "INCOME": 1, "BALANCED": 2, "GROWTH": 3, "AGGRESSIVE_GROWTH": 4},
}


def risk_policy_v1() -> dict[str, Any]:
    """The seeded v1 risk policy definition (prompts/labels from the seed file, points checked by tests)."""
    data = json.loads((SEED_DIR / "policies" / "risk_policy_v1.json").read_text(encoding="utf-8"))
    definition: dict[str, Any] = data["definition"]
    return definition


def template_v1() -> dict[str, Any]:
    return copy.deepcopy(TEMPLATE_V1)


def risk_policy_v2_ac_10_1() -> dict[str, Any]:
    """AC-10.1: MODERATE 12-19 and AGGRESSIVE 20-28."""
    definition = risk_policy_v1()
    definition["bands"] = [
        {"band": "CONSERVATIVE", "min_score": 0, "max_score": 11},
        {"band": "MODERATE", "min_score": 12, "max_score": 19},
        {"band": "AGGRESSIVE", "min_score": 20, "max_score": 28},
    ]
    return definition


def template_with(band: str, asset_class: str, value: Any) -> dict[str, Any]:
    definition = template_v1()
    definition["templates"][band][asset_class] = value
    return definition
