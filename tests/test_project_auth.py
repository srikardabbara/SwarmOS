"""Project keys scope traces, and the API does not edit workflow files."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_db_dir) / 'auth.db'}"
os.environ["SWARMOS_DASHBOARD_ORIGIN"] = "http://localhost:3000"

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402
from backend.models.database import init_db, normalize_database_url  # noqa: E402

init_db()
client = TestClient(app)


def test_postgres_url_uses_psycopg_driver():
    assert normalize_database_url("postgres://user:pass@localhost/swarmos") == (
        "postgresql+psycopg://user:pass@localhost/swarmos"
    )
    assert normalize_database_url("sqlite:///./swarmos.db") == "sqlite:///./swarmos.db"


def _trace(trace_id: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": trace_id,
        "workflow_id": "cancel-subscription",
        "started_at": now,
        "completed_at": now,
        "status": "completed",
        "input_data": {},
        "metadata": {
            "communication_review": {
                "findings": [{"id": "finding-1", "fix": {"action": "preserve_keys", "agent": "billing", "keys": ["user_id"]}}]
            }
        },
        "events": [],
        "validation_results": [],
    }


def test_traces_require_a_project_key_and_stay_inside_that_project():
    created = client.post("/projects", json={"name": "Billing handoff"})
    assert created.status_code == 201
    key = created.json()["api_key"]
    assert key.startswith("swarmos_")
    assert "key_hash" not in created.json()

    denied = client.get("/traces")
    assert denied.status_code == 401

    headers = {"Authorization": f"Bearer {key}"}
    assert client.get("/projects/current", headers=headers).json()["name"] == "Billing handoff"

    posted = client.post("/traces", json=_trace("trace-billing"), headers=headers)
    assert posted.status_code == 201

    other = client.post("/projects", json={"name": "Other"})
    other_headers = {"Authorization": f"Bearer {other.json()['api_key']}"}
    assert client.get("/traces/trace-billing", headers=other_headers).status_code == 404
    assert client.get("/traces", headers=other_headers).json() == []
    assert client.get("/traces", headers=headers).json()[0]["id"] == "trace-billing"

    missing_fix = client.post("/traces/trace-billing/fixes/finding-1", headers=headers)
    assert missing_fix.status_code == 404


def test_blank_project_name_is_rejected():
    response = client.post("/projects", json={"name": "   "})
    assert response.status_code == 400
