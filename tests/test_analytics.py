from fastapi import status


def test_analytics_empty_applications(client, another_auth_headers):
    # another_user has 0 applications
    response = client.get("/api/v1/analytics", headers=another_auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_applications"] == 0
    assert data["overall_response_rate"] == 0.0
    assert data["weekly_trends"] == []


def test_analytics_with_applications(client, auth_headers, test_company):
    # Create applications in varied statuses
    client.post(
        "/api/v1/applications",
        json={"job_title": "App 1", "company_id": test_company.id, "status": "Applied"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/applications",
        json={"job_title": "App 2", "company_id": test_company.id, "status": "Interview"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/applications",
        json={"job_title": "App 3", "company_id": test_company.id, "status": "Offer"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/applications",
        json={"job_title": "App 4", "company_id": test_company.id, "status": "Rejected"},
        headers=auth_headers,
    )

    response = client.get("/api/v1/analytics", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_applications"] >= 4
    # Status breakdown
    breakdown_map = {item["status"]: item["count"] for item in data["status_breakdown"]}
    assert breakdown_map.get("Applied", 0) >= 1
    assert breakdown_map.get("Interview", 0) >= 1
    assert breakdown_map.get("Offer", 0) >= 1
    assert breakdown_map.get("Rejected", 0) >= 1

    # Response rate check: Interview + Offer + Rejected are responses
    assert data["overall_response_rate"] > 0
    assert data["interview_conversion_rate"] > 0
    assert len(data["weekly_trends"]) >= 1
    weekly = data["weekly_trends"][0]
    assert weekly["applications_submitted"] >= 1
    assert "week_start" in weekly
