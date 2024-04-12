from fastapi import status
from fastapi.testclient import TestClient
from app.main import app
from app.db.conn import SessionLocal
from app.models.user import User

client = TestClient(app)


def test_create_user():
    # Creating a new user
    response = client.post(
        "/users/",
        json={
            "username": "testuser",
            "email": "test@email.com",
            "full_name": "Test User",
            "hashed_password": "hashedpassword123",  # In a real-world scenario, this should be hashed
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "User created successfully"
    user_id = response.json()["user_id"]

    # Validate database
    db = SessionLocal()
    db_user = db.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    db.close()
