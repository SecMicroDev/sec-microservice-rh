from fastapi.testclient import TestClient
from app.models.enterprise import BaseEnterprise, EnterpriseUpdate
from app.models.user import FirstUserCreate


def test_create_enterprise(test_client_authenticated_default: TestClient):
    client = test_client_authenticated_default

    enterprise_data = BaseEnterprise(
        name="Test Enterprise",
        accountable_email="enterprise_test@test.mail.com",
        activity_type="Test Activity",
    )
    user_data = FirstUserCreate(
        username="testuser",
        password="testpassword",
        email="enterprise_test@test.mail.com",
    )
    response = client.post(
        "/enterprise/signup",
        json={
            "enterprise": enterprise_data.model_dump(),
            "user": user_data.model_dump(),
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["username"] == user_data.username
    assert response.json()["data"]["enterprise"]["name"] == enterprise_data.name


def test_get_enterprise(test_client_authenticated_default: TestClient):
    client = test_client_authenticated_default

    response = client.get("/enterprise")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Jarucucu"
    assert response.json()["data"]["id"] is not None


def test_get_full_enterprise(test_client_authenticated_default: TestClient):
    client = test_client_authenticated_default

    response = client.get("/enterprise/full")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Jarucucu"

    assert len(response.json()["data"]["roles"]) > 0
    for role in response.json()["data"]["roles"]:
        assert role["name"] is not None

    assert len(response.json()["data"]["scopes"]) > 0
    for scope in response.json()["data"]["scopes"]:
        assert scope["name"] is not None

    assert response.json()["data"]["users"][0]["username"] == "testuser"


def test_update_enterprise(test_client_authenticated_default: TestClient):
    client = test_client_authenticated_default

    enterprise_data = EnterpriseUpdate(
        name="Updated Test Enterprise", description="Updated Test Description"
    )
    response = client.put("/enterprise", content=enterprise_data.model_dump_json())
    assert response.status_code == 200
    assert response.json()["data"]["name"] == enterprise_data.name


def test_delete_enterprise(test_client_authenticated_default: TestClient):
    client = test_client_authenticated_default

    response = client.delete("/enterprise")
    assert response.status_code == 200
    assert response.json()["message"] == "Enterprise deleted"
