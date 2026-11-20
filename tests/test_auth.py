from fastapi import status


def test_register_user_success(client):
    payload = {
        "email": "newuser@example.com",
        "password": "Password123!",
        "full_name": "Taylor Swift",
        "resume_text": "Experienced vocalist and software advocate.",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "Taylor Swift"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email_fails(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "Password123!",
        "full_name": "Duplicate Tester",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]


def test_register_invalid_email_fails(client):
    payload = {
        "email": "not-an-email",
        "password": "Password123!",
        "full_name": "Bad Email User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_success(client, test_user):
    # Form login (standard OAuth2)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "SecretPassword123!"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_json_success(client, test_user):
    # JSON login
    response = client.post(
        "/api/v1/auth/login/json",
        json={"email": test_user.email, "password": "SecretPassword123!"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data


def test_login_invalid_password_fails(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "WrongPassword999"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_me(client, auth_headers, test_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name


def test_get_current_user_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_current_user_profile(client, auth_headers):
    payload = {
        "full_name": "Alex Mercer, Senior Engineer",
        "resume_text": "Updated resume text with Kubernetes and AWS experience.",
    }
    response = client.put("/api/v1/auth/me", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["full_name"] == "Alex Mercer, Senior Engineer"
    assert "Kubernetes" in data["resume_text"]
