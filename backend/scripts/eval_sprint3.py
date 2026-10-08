"""Evaluate Sprint 3 contract (sprint-contracts/sprint-3.json) against fresh eval.db."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.core.clock import AnchoredClock
from app.core.config import Settings
from app.core.db import build_engine
from app.main import create_app

WORKSPACE = Path(__file__).resolve().parents[2]
CONTRACT_PATH = WORKSPACE / "sprint-contracts" / "sprint-3.json"
EVAL_DB_PATH = Path("/tmp/wealthwise_eval_sprint3.db")


def main() -> None:
    if EVAL_DB_PATH.exists():
        EVAL_DB_PATH.unlink()

    with CONTRACT_PATH.open("r", encoding="utf-8") as f:
        contract = json.load(f)

    db_url = f"sqlite:///{EVAL_DB_PATH}"
    settings = Settings(database_url=db_url, auth_token_secret="eval-secret", stub_auth_enabled=True)
    engine = build_engine(db_url)
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(WORKSPACE / "backend" / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    clock = AnchoredClock(datetime(2026, 1, 15, 9, 0, tzinfo=UTC))
    app = create_app(settings, clock=clock)

    passed = 0
    failed = 0

    with TestClient(app) as client:
        # Setup: Alice needs an assessment & recommendation for rebalancing evaluate (api-s3-005)
        alice_hdr = {"Authorization": "Bearer stub-token-alice"}
        bob_hdr = {"Authorization": "Bearer stub-token-bob"}

        # Alice assessment
        q_resp = client.get("/api/v1/risk-profile/questionnaire", headers=alice_hdr)
        q_data = q_resp.json()
        policy_version_id = q_data["policy_version_id"]
        answers_alice = [
            {"question_code": q["code"], "option_code": q["options"][2]["code"]}
            for q in q_data["questions"]
        ]
        r = client.post(
            "/api/v1/risk-profile/assessments",
            headers=alice_hdr,
            json={"policy_version_id": policy_version_id, "answers": answers_alice},
        )
        assert r.status_code == 201

        # Alice recommendation
        r = client.post("/api/v1/recommendations", headers=alice_hdr, json={})
        assert r.status_code == 201

        # Bob assessment (for override check api-s3-007)
        answers_bob = [
            {"question_code": q["code"], "option_code": q["options"][3]["code"]}
            for q in q_data["questions"]
        ]
        r_b = client.post(
            "/api/v1/risk-profile/assessments",
            headers=bob_hdr,
            json={"policy_version_id": policy_version_id, "answers": answers_bob},
        )
        assert r_b.status_code == 201

        for check in contract["contract"]["api_checks"]:
            cid = check["id"]
            method = check["method"]
            path = check["path"]
            headers = check.get("headers", {})
            body = check.get("body")
            expected_status = check["expected_status"]
            expected_body = check.get("expected_body")

            print(f"Running check {cid}: {method} {path} ...", end=" ")
            resp = client.request(method, path, headers=headers, json=body)

            if resp.status_code != expected_status:
                print(f"FAILED (expected status {expected_status}, got {resp.status_code}) -> {resp.text}")
                failed += 1
                continue

            if expected_body is not None:
                actual = resp.json()
                mismatch = False
                for k, v in expected_body.items():
                    if isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if actual.get(k, {}).get(sub_k) != sub_v:
                                print(f"FAILED (nested key '{k}.{sub_k}': expected {sub_v!r}, got {actual.get(k, {}).get(sub_k)!r})")
                                mismatch = True
                                break
                    elif actual.get(k) != v:
                        print(f"FAILED (key '{k}': expected {v!r}, got {actual.get(k)!r})")
                        mismatch = True
                        break
                if mismatch:
                    failed += 1
                    continue

            print("PASS")
            passed += 1

    print(f"\nTotal: {passed + failed}, Passed: {passed}, Failed: {failed}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
