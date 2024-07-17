""" Tests for the User route with client """

from typing import Any

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.data_hash import validate_hashed_data
from app.models.enterprise import EnterpriseRelation
from app.models.role import DefaultRole, Role, RoleRelation
from app.models.scope import DefaultScope, Scope, ScopeRelation
from app.models.user import User, UserRead

from .conftest import get_test_client_authenticated


def _create_user_schema(**kwargs):
    role: Role = list(
        filter(
            lambda x: x.name == DefaultRole.COLLABORATOR.value, kwargs.get("roles", [])
        )
    )[0]
    scope: Scope = list(
        filter(
            lambda x: x.name == DefaultScope.PATRIMONIAL.value, kwargs.get("scopes", [])
        )
    )[0]
    enterprise = kwargs.get("enterprise")

    return {
        "username": "testuser2",
        "email": "test2@email.com",
        "full_name": "Test User 2",
        "hashed_password": "mypassword12345678",
        "enterprise_id": enterprise.id,
        "role_id": role.id,
        "scope_id": scope.id,
    }


def _create_user_on_db(session: Session, **kwargs) -> UserRead:
    user: User | None = None
    user_read: UserRead | None = None

    user = User(**_create_user_schema(**kwargs))
    session.add(user)
    session.commit()
    session.refresh(user)

    user_read = UserRead(
        **user.model_dump(),
        role=RoleRelation(**user.role.model_dump()),
        scope=ScopeRelation(**user.scope.model_dump()),
        enterprise=EnterpriseRelation(**user.enterprise.model_dump()),
    )

    return user_read


def test_wrong_attribute(
    enterprise_role_scope: dict[str, Any],
    test_client_authenticated_default: TestClient,
):
    """User should be created"""

    test_client = test_client_authenticated_default

    response = test_client.post(
        "/users/",
        json={
            "username": "testuser",
            "email": "test@email.com",
            "full_name": "Test User",
            "hashed_password": "hashedpassword123",
            "enterprise_id": enterprise_role_scope["enterprise"].id,
            "role_id": enterprise_role_scope["roles"][0].id,
            "scope_id": enterprise_role_scope["scopes"][0].id,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_user(
    enterprise_role_scope: dict[str, Any],
    db_session: Session,
    test_client_authenticated_default: TestClient,
):
    """User should be created"""

    test_client = test_client_authenticated_default

    # Creating a new user
    response = test_client.post(
        "/users/",
        json={
            "username": "testuser2",
            "email": "test2@email.com",
            "full_name": "Test User 2",
            "password": "mypassword12345678",
            "enterprise_id": enterprise_role_scope["enterprise"].id,
            "role_id": enterprise_role_scope["roles"][0].id,
            "scope_id": enterprise_role_scope["scopes"][0].id,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["status"] == 201
    assert response.json()["message"] == "User created"
    user = response.json()["data"]

    # Validate database
    print(user)
    db = db_session
    db_user_query = db.get(User, User.id)
    db_user = db_user_query

    assert db_user is not None

    user_id = db_user.id

    assert db_user is not None
    assert user_id is not None
    assert user_id == user["id"]
    assert db_user.username == user["username"]
    assert db_user.enterprise is not None
    assert db_user.enterprise.id is not None
    assert db_user.enterprise.name == enterprise_role_scope["enterprise"].name
    assert db_user.role is not None
    assert db_user.role.name == enterprise_role_scope["roles"][0].name
    assert db_user.scope is not None
    assert db_user.scope.name == enterprise_role_scope["scopes"][0].name

    db.close()


def test_user_unauthorized_to_create(
    db_session: Session, enterprise_role_scope: dict[str, Any]
):
    """User should not be created"""
    # db_session = next(db_session_manual())
    user: UserRead | None = None
    role_id = list(
        map(
            lambda x: x.id,
            filter(
                lambda x: x.name == DefaultRole.COLLABORATOR,
                enterprise_role_scope["roles"],
            ),
        )
    )[0]

    scope_id = list(
        map(
            lambda x: x.id,
            filter(
                lambda x: x.name == DefaultScope.SELLS, enterprise_role_scope["scopes"]
            ),
        )
    )[0]

    with db_session:
        user = _create_user_on_db(db_session, **enterprise_role_scope)

    session, connection, transaction, test_client = next(
        get_test_client_authenticated(user=user)
    )

    # Creating a new user
    resp = test_client.post(
        "/users/",
        json={
            "username": "testuser3",
            "email": "testemail3@test.mail.com",
            "full_name": "Test User 3",
            "password": "mypassword",
            "enterprise_id": user.enterprise_id,
            "role_id": role_id,
            "scope_id": scope_id,
        },
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN

    transaction.rollback()

    if session.is_active:
        session.close()

    connection.close()


def test_get_current_user(
    create_default_user: dict[str, Any],
    test_client_authenticated_default: TestClient,
):
    """Current user should be retrieved"""
    test_client = test_client_authenticated_default
    response = test_client.get("/users/me")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == 200
    assert response.json()["message"] == "Current user retrieved"

    user_data: dict[str, Any] = response.json()["data"]
    user: UserRead = UserRead(**user_data)

    assert user.id == create_default_user["user"].id
    assert user.username == create_default_user["user"].username
    assert user.email == create_default_user["user"].email
    assert user.role.id == create_default_user["user"].role_id
    assert user.scope.id == create_default_user["user"].scope_id
    assert user.enterprise.id == create_default_user["user"].enterprise_id


def test_update_current_user(
    test_client_authenticated_default: TestClient,
    create_default_user: dict[str, Any],
    db_session: Session,
):
    """Current user should be updated"""
    test_client = test_client_authenticated_default
    # Update user information
    response = test_client.put(
        "/users/me",
        json={
            "username": "newusername",
            "email": "newemail@example.com",
            "full_name": "New User",
            "password": "newpassword",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == 200
    assert response.json()["message"] == "Current user updated"

    with db_session as session:
        updated_user = session.get(User, create_default_user["user"].id)

        assert updated_user.username == "newusername"
        assert updated_user.email == "newemail@example.com"
        assert updated_user.full_name == "New User"
        assert validate_hashed_data("newpassword", updated_user.hashed_password)


def test_get_user(
    test_client_authenticated_default: TestClient,
    create_default_user: dict[str, Any],
):
    """User should be retrieved"""
    test_client = test_client_authenticated_default
    user_id = create_default_user["user"].id  # Replace with the desired user ID
    response = test_client.get(f"users/{user_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == 200
    assert response.json()["message"] == "User retrieved"

    user = response.json()["data"]
    db_user = create_default_user["user"]

    for key in ["id", "username", "email", "full_name", "enterprise_id"]:
        assert user[key] == getattr(db_user, key)


def test_get_all_users(
    test_client_authenticated_default: TestClient,
    create_default_user: dict[str, Any],
    db_session: Session,
):
    # pylint: disable=unused-argument

    """All users should be retrieved"""

    test_client = test_client_authenticated_default

    test_client.post(
        "/users/",
        json={
            "username": "testuser3",
            "email": "testemail3@test.mail.com",
            "full_name": "Test User 3",
            "password": "mypassword",
            "enterprise_id": create_default_user["user"].enterprise_id,
            "role_id": create_default_user["roles"][0].id,
            "scope_id": create_default_user["scopes"][0].id,
        },
    )

    response = test_client.get("users/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == 200
    assert response.json()["message"] == "Users retrieved"

    users = response.json()["data"]
    assert len(users) == 2


def test_update_user(
    test_client_authenticated_default: TestClient,
    db_session: Session,
):
    """User should be updated"""

    test_client = test_client_authenticated_default
    user_id = 1  # Replace with the desired user ID

    # Update user information
    response = test_client.put(
        f"users/{user_id}",
        json={
            "username": "newusername",
            "email": "newemail@example.com",
            "full_name": "New User",
            "password": "newpassword",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == 200
    assert response.json()["message"] == "User updated"
    user = response.json()["data"]

    with db_session as session:
        updated_user = session.get(User, user_id)

        assert updated_user.username == user["username"]
        assert updated_user.email == user["email"]
        assert updated_user.full_name == user["full_name"]
        assert validate_hashed_data("newpassword", updated_user.hashed_password)


def test_delete_user(
    test_client_authenticated_default: TestClient,
    db_session: Session,
):
    """User should be deleted"""

    test_client = test_client_authenticated_default
    user_id = 1  # Replace with the desired user ID
    response = test_client.delete(f"users/{user_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == 200
    assert response.json()["message"] == "User deleted"

    with db_session as session:
        assert session.get(User, user_id) is None
