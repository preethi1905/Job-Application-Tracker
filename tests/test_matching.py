from fastapi import status


def test_match_application_with_explicit_jd_and_resume(client, auth_headers, test_company):
    # Create application
    app_res = client.post(
        "/api/v1/applications",
        json={
            "job_title": "Senior Python Backend Engineer",
            "company_id": test_company.id,
            "status": "Applied",
        },
        headers=auth_headers,
    )
    app_id = app_res.json()["id"]

    match_payload = {
        "job_description": (
            "We are seeking a Backend Engineer with strong expertise in Python, FastAPI, "
            "PostgreSQL, SQLAlchemy, Docker, Redis, Kubernetes, and AWS. Must be familiar with Git and REST APIs."
        ),
        "resume_text": (
            "Backend developer with 4 years of experience in Python, FastAPI, PostgreSQL, "
            "SQLAlchemy, Docker, Git, and REST APIs. Built microservices and increased test coverage by 40%."
        ),
    }

    response = client.post(
        f"/api/v1/applications/{app_id}/match",
        json=match_payload,
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["application_id"] == app_id
    assert data["match_score"] > 50.0
    assert "rating" in data
    assert "summary" in data

    # Check matching keywords
    matching = [k.lower() for k in data["matching_keywords"]]
    assert "python" in matching
    assert "fastapi" in matching
    assert "postgresql" in matching
    assert "docker" in matching

    # Check missing keywords (kubernetes, redis, aws)
    missing = [k.lower() for k in data["missing_keywords"]]
    assert "kubernetes" in missing or "redis" in missing or "aws" in missing

    # Check categories and suggestions
    assert len(data["category_scores"]) > 0
    assert len(data["suggestions"]) > 0
    assert data["engine"].startswith("Heuristic-NLP-Matcher")


def test_match_application_using_profile_resume_and_saved_jd(client, auth_headers, test_company):
    # test_user already has resume_text in fixture
    app_res = client.post(
        "/api/v1/applications",
        json={
            "job_title": "Full Stack Engineer",
            "company_id": test_company.id,
            "job_description": (
                "Looking for an engineer with Python, FastAPI, Docker, and Git experience."
            ),
            "status": "Applied",
        },
        headers=auth_headers,
    )
    app_id = app_res.json()["id"]

    # Pass empty body -> should fall back to application.job_description and user.resume_text
    response = client.post(
        f"/api/v1/applications/{app_id}/match",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["match_score"] > 50.0
    matching = [k.lower() for k in data["matching_keywords"]]
    assert "python" in matching
    assert "fastapi" in matching


def test_match_application_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/applications/99999/match",
        json={"job_description": "Any JD text"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_match_application_missing_resume_fails(client, another_auth_headers, test_company):
    # Clear resume on another_user
    client.put("/api/v1/auth/me", json={"resume_text": ""}, headers=another_auth_headers)

    app_res = client.post(
        "/api/v1/applications",
        json={"job_title": "Dev", "company_id": test_company.id, "status": "Applied"},
        headers=another_auth_headers,
    )
    app_id = app_res.json()["id"]

    response = client.post(
        f"/api/v1/applications/{app_id}/match",
        json={"job_description": "Python developer needed", "resume_text": ""},
        headers=another_auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "No resume text provided" in response.json()["detail"]
