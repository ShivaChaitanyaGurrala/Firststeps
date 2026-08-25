def test_add_to_watchlist(client, sample_title):
    resp = client.post("/watchlist", json={"title_id": sample_title.id, "notes": "weekend"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title_id"] == sample_title.id
    assert body["title"] == "Inception"
    assert body["notes"] == "weekend"


def test_add_to_watchlist_unknown_title_404(client):
    resp = client.post("/watchlist", json={"title_id": 999999})
    assert resp.status_code == 404


def test_add_to_watchlist_is_idempotent(client, sample_title):
    first = client.post("/watchlist", json={"title_id": sample_title.id})
    second = client.post("/watchlist", json={"title_id": sample_title.id})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get("/watchlist").json()) == 1


def test_remove_from_watchlist(client, sample_title):
    entry_id = client.post("/watchlist", json={"title_id": sample_title.id}).json()["id"]
    resp = client.delete(f"/watchlist/{entry_id}")
    assert resp.status_code == 204
    assert client.get("/watchlist").json() == []


def test_remove_from_watchlist_404(client):
    resp = client.delete("/watchlist/999999")
    assert resp.status_code == 404


def test_rate_title(client, sample_title):
    resp = client.post("/ratings", json={"title_id": sample_title.id, "score": 9, "review": "great"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["score"] == 9
    assert body["review"] == "great"


def test_rate_title_rejects_out_of_range_score(client, sample_title):
    resp = client.post("/ratings", json={"title_id": sample_title.id, "score": 11})
    assert resp.status_code == 422


def test_rate_title_upserts_on_repeat(client, sample_title):
    client.post("/ratings", json={"title_id": sample_title.id, "score": 5})
    resp = client.post("/ratings", json={"title_id": sample_title.id, "score": 8})
    assert resp.status_code == 201
    assert resp.json()["score"] == 8
    assert len(client.get("/ratings").json()) == 1


def test_create_list_and_add_item(client, sample_title):
    list_resp = client.post("/lists", json={"name": "Weekend picks"})
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    add_resp = client.post(f"/lists/{list_id}/items", json={"title_id": sample_title.id})
    assert add_resp.status_code == 201
    body = add_resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["title_id"] == sample_title.id

    remove_resp = client.delete(f"/lists/{list_id}/items/{sample_title.id}")
    assert remove_resp.status_code == 204
    assert client.get(f"/lists/{list_id}").json()["items"] == []
