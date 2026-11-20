from datetime import date
from fastapi import status
from app.models.application import ApplicationStatus


def test_create_application_with_company_name(client, auth_headers):
    payload = {
        "job_title": "Senior Backend Engineer",
        "company_name": "Netflix Inc",
        "job_description": "Building high-performance video streaming microservices using Python, FastAPI, and PostgreSQL.",
        "status": "Applied",
        "location": "Los Gatos, CA",
        "salary_min": 180000.0,
        "salary_max": 230000.0,
        "currency": "USD",
        "notes": "Referred by former colleague.",
        "status_notes": "Submitted via internal referral link.",
    }
    response = client.post("/api/v1/applications", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["job_title"] == "Senior Backend Engineer"
    assert data["status"] == "Applied"
    assert data["company"] is not None
    assert data["company"]["name"] == "Netflix Inc"
    assert len(data["status_history"]) == 1
    assert data["status_history"][0]["new_status"] == "Applied"
    assert "internal referral" in data["status_history"][0]["notes"]


def test_create_application_with_company_id(client, auth_headers, test_company):
    payload = {
        "job_title": "Staff Platform Engineer",
        "company_id": test_company.id,
        "job_description": "Lead distributed database and payments infrastructure with Docker and AWS.",
        "status": "Applied",
        "applied_date": str(date.today()),
    }
    response = client.post("/api/v1/applications", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["company_id"] == test_company.id
    assert data["company"]["name"] == test_company.name


def test_list_applications_pagination_and_filter(client, auth_headers, test_company):
    # Create 3 applications
    client.post(
        "/api/v1/applications",
        json={"job_title": "Backend Python Dev", "company_id": test_company.id, "status": "Applied"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/applications",
        json={"job_title": "Full Stack Dev", "company_id": test_company.id, "status": "Interview"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/applications",
        json={"job_title": "Cloud Architect", "company_id": test_company.id, "status": "Offer"},
        headers=auth_headers,
    )

    # 1. Total count
    res_all = client.get("/api/v1/applications?page=1&page_size=10", headers=auth_headers)
    assert res_all.status_code == status.HTTP_200_OK
    data_all = res_all.json()
    assert data_all["total"] >= 3
    assert len(data_all["items"]) >= 3

    # 2. Filter by status: Interview
    res_int = client.get("/api/v1/applications?status=Interview", headers=auth_headers)
    assert res_int.status_code == status.HTTP_200_OK
    data_int = res_int.json()
    for item in data_int["items"]:
        assert item["status"] == "Interview"

    # 3. Search query: "Cloud"
    res_search = client.get("/api/v1/applications?search=Cloud", headers=auth_headers)
    assert res_search.status_code == status.HTTP_200_OK
    data_search = res_search.json()
    assert any("Cloud" in item["job_title"] for item in data_search["items"])


def test_update_application_status_creates_history(client, auth_headers, test_company):
    # 1. Create application
    create_res = client.post(
        "/api/v1/applications",
        json={"job_title": "Site Reliability Engineer", "company_id": test_company.id, "status": "Applied"},
        headers=auth_headers,
    )
    app_id = create_res.json()["id"]

    # 2. Transition status: Applied -> Interview
    update_res = client.put(
        f"/api/v1/applications/{app_id}",
        json={"status": "Interview", "status_notes": "HR Screening round scheduled for Friday."},
        headers=auth_headers,
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["status"] == "Interview"

    # 3. Fetch status history timeline
    history_res = client.get(f"/api/v1/applications/{app_id}/history", headers=auth_headers)
    assert history_res.status_code == status.HTTP_200_OK
    history_items = history_res.json()
    assert len(history_items) >= 2
    # Latest should be transition to Interview
    latest = history_items[0]
    assert latest["old_status"] == "Applied"
    assert latest["new_status"] == "Interview"
    assert "HR Screening" in latest["notes"]


def test_user_cannot_access_other_users_applications(
    client, auth_headers, another_auth_headers, test_company
):
    # User 1 creates application
    res_user1 = client.post(
        "/api/v1/applications",
        json={"job_title": "Private Application", "company_id": test_company.id, "status": "Applied"},
        headers=auth_headers,
    )
    app_id = res_user1.json()["id"]

    # User 2 attempts to get application -> should be 404 (not found in user 2's scope)
    res_user2_get = client.get(f"/api/v1/applications/{app_id}", headers=another_auth_headers)
    assert res_user2_get.status_code == status.HTTP_404_NOT_FOUND

    # User 2 attempts to update application -> 404
    res_user2_put = client.put(
        f"/api/v1/applications/{app_id}",
        json={"job_title": "Hijacked Title"},
        headers=another_auth_headers,
    )
    assert res_user2_put.status_code == status.HTTP_404_NOT_FOUND

    # User 2 attempts to delete application -> 404
    res_user2_del = client.delete(f"/api/v1/applications/{app_id}", headers=another_auth_headers)
    assert res_user2_del.status_code == status.HTTP_404_NOT_FOUND


def test_delete_application(client, auth_headers, test_company):
    create_res = client.post(
        "/api/v1/applications",
        json={"job_title": "Temporary Job", "company_id": test_company.id, "status": "Applied"},
        headers=auth_headers,
    )
    app_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
