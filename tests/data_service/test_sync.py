from data_service.routers import sync as sync_router


def test_list_sync_runs_empty(client):
    assert client.get("/sync/runs").json() == []


def test_trigger_bulk_seed_creates_run_and_dispatches_background_task(client, monkeypatch):
    calls = []

    async def fake_run(*args, run_id=None, **kwargs):
        calls.append({"args": args, "run_id": run_id, "kwargs": kwargs})

    monkeypatch.setattr(sync_router.bulk_seed, "run", fake_run)

    resp = client.post("/sync/trigger", json={"run_type": "bulk_seed"})
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert isinstance(body["run_id"], int)

    # TestClient runs background tasks synchronously before returning, so the
    # fake_run stub should already have been invoked with the created run_id.
    assert len(calls) == 1
    assert calls[0]["run_id"] == body["run_id"]

    run_resp = client.get(f"/sync/runs/{body['run_id']}")
    assert run_resp.status_code == 200
    assert run_resp.json()["run_type"] == "bulk_seed"


def test_trigger_daily_sync_creates_run_and_dispatches_background_task(client, monkeypatch):
    calls = []

    async def fake_run(*args, run_id=None, **kwargs):
        calls.append(run_id)

    monkeypatch.setattr(sync_router.daily_sync, "run", fake_run)

    resp = client.post("/sync/trigger", json={"run_type": "daily_sync"})
    assert resp.status_code == 202
    body = resp.json()
    assert calls == [body["run_id"]]


def test_get_sync_run_404(client):
    assert client.get("/sync/runs/999999").status_code == 404
