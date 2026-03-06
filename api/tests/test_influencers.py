from fastapi.testclient import TestClient


def test_create_influencer(client: TestClient, test_org):
    resp = client.post(
        "/influencers",
        params={"org_id": test_org.id},
        json={
            "name": "Novo Influencer",
            "type": "brand",
            "niche": "food",
            "tone": "casual",
            "emoji_level": "medium",
            "forbidden_words": ["proibido"],
            "language": "pt-BR",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Novo Influencer"
    assert data["org_id"] == test_org.id
    assert data["niche"] == "food"
    assert data["forbidden_words"] == ["proibido"]


def test_list_influencers(client: TestClient, test_influencer, test_org):
    resp = client.get("/influencers", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(inf["id"] == test_influencer.id for inf in data)


def test_get_influencer(client: TestClient, test_influencer):
    resp = client.get(f"/influencers/{test_influencer.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == test_influencer.id
    assert data["name"] == test_influencer.name


def test_get_influencer_not_found(client: TestClient):
    resp = client.get("/influencers/nonexistent-id")
    assert resp.status_code == 404


def test_update_influencer(client: TestClient, test_influencer):
    resp = client.patch(
        f"/influencers/{test_influencer.id}",
        json={"name": "Updated Name", "tone": "funny"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["tone"] == "funny"


def test_update_influencer_not_found(client: TestClient):
    resp = client.patch(
        "/influencers/nonexistent-id",
        json={"name": "X"},
    )
    assert resp.status_code == 404


def test_upsert_brand_kit_create(client: TestClient, test_influencer):
    resp = client.post(
        f"/influencers/{test_influencer.id}/brand-kit",
        json={
            "description": "Kit da marca",
            "value_props": {"qualidade": "premium"},
            "products": {"produto1": "Mel puro"},
            "audience": {"faixa": "25-45"},
            "style_guidelines": {"fonte": "Inter"},
            "links": {"site": "https://example.com"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Kit da marca"
    assert data["value_props"]["qualidade"] == "premium"
    assert data["influencer_id"] == test_influencer.id


def test_upsert_brand_kit_update(client: TestClient, test_influencer):
    # Create first
    client.post(
        f"/influencers/{test_influencer.id}/brand-kit",
        json={"description": "v1"},
    )

    # Update (upsert)
    resp = client.post(
        f"/influencers/{test_influencer.id}/brand-kit",
        json={"description": "v2", "products": {"novo": "produto"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "v2"
    assert data["products"]["novo"] == "produto"


def test_get_brand_kit(client: TestClient, test_influencer):
    # Create
    client.post(
        f"/influencers/{test_influencer.id}/brand-kit",
        json={"description": "Test kit"},
    )

    resp = client.get(f"/influencers/{test_influencer.id}/brand-kit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Test kit"


def test_get_brand_kit_not_found(client: TestClient, test_influencer):
    resp = client.get(f"/influencers/{test_influencer.id}/brand-kit")
    assert resp.status_code == 404
