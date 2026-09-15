def test_register_and_me(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "new@test.com", "password": "secret12", "full_name": "New User"},
    )
    assert r.status_code == 201
    login = client.post(
        "/api/auth/login",
        data={"username": "new@test.com", "password": "secret12"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new@test.com"


def test_spaces_require_auth(client):
    r = client.get("/api/spaces")
    assert r.status_code == 401
