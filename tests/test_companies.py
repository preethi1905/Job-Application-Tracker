from fastapi import status


def test_create_company(client, auth_headers):
    payload = {
        "name": "Datadog Cloud",
        "website": "https://datadoghq.com",
        "location": "New York, NY",
        "industry": "Observability & Cloud Monitoring",
    }
    response = client.post("/api/v1/companies", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Datadog Cloud"
    assert data["industry"] == "Observability & Cloud Monitoring"
    assert "id" in data


def test_create_duplicate_company_fails(client, auth_headers, test_company):
    payload = {"name": test_company.name}
    response = client.post("/api/v1/companies", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]


def test_list_companies(client, auth_headers, test_company):
    response = client.get("/api/v1/companies", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    names = [c["name"] for c in data]
    assert test_company.name in names


def test_search_companies(client, auth_headers, test_company):
    response = client.get("/api/v1/companies?search=Stripe", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Stripe Tech"


def test_get_company_by_id(client, auth_headers, test_company):
    response = client.get(f"/api/v1/companies/{test_company.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_company.id
    assert data["name"] == test_company.name


def test_get_nonexistent_company_fails(client, auth_headers):
    response = client.get("/api/v1/companies/99999", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_company(client, auth_headers, test_company):
    payload = {"industry": "FinTech & Global Payments"}
    response = client.put(f"/api/v1/companies/{test_company.id}", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["industry"] == "FinTech & Global Payments"


def test_delete_company(client, auth_headers):
    # Create temporary company to delete
    create_res = client.post("/api/v1/companies", json={"name": "To Delete Inc"}, headers=auth_headers)
    comp_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/companies/{comp_id}", headers=auth_headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = client.get(f"/api/v1/companies/{comp_id}", headers=auth_headers)
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
