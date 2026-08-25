def test_list_titles_empty(client):
    resp = client.get("/titles")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_titles_returns_seeded_title(client, sample_title):
    resp = client.get("/titles")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == sample_title.id
    assert body[0]["title"] == "Inception"


def test_list_titles_filters_by_query(client, sample_title):
    assert len(client.get("/titles", params={"q": "incep"}).json()) == 1
    assert len(client.get("/titles", params={"q": "nomatch"}).json()) == 0


def test_get_title_detail(client, sample_title):
    resp = client.get(f"/titles/{sample_title.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sample_title.id
    assert body["genres"] == []
    assert body["cast"] == []


def test_get_title_detail_404(client):
    resp = client.get("/titles/999999")
    assert resp.status_code == 404
