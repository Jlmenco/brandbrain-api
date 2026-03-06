from fastapi.testclient import TestClient


def test_register(client: TestClient):
    resp = client.post(
        "/auth/register",
        json={"email": "new@brandbrain.dev", "password": "pass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "new@brandbrain.dev"
    assert data["name"] == "new"
    assert "id" in data


def test_register_duplicate(client: TestClient, test_user):
    resp = client.post(
        "/auth/register",
        json={"email": test_user.email, "password": "pass123"},
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_login(client: TestClient, test_user):
    resp = client.post(
        "/auth/login",
        json={"email": "test@brandbrain.dev", "password": "test123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, test_user):
    resp = client.post(
        "/auth/login",
        json={"email": "test@brandbrain.dev", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    resp = client.post(
        "/auth/login",
        json={"email": "nobody@brandbrain.dev", "password": "pass123"},
    )
    assert resp.status_code == 401


def test_me(client: TestClient, test_user):
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name


def test_logout(client: TestClient):
    resp = client.post("/auth/logout")
    assert resp.status_code == 200
