from collections.abc import Generator
import datetime
import json
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session, select

from app.messages.event import UpdateEvent
from app.models.enterprise import Enterprise
from app.models.user import User
from .conftest import engine


@pytest.fixture(scope="function")
def setup_db() -> Engine:
    SQLModel.metadata.create_all(bind=engine)
    return engine


def gen_db(session: Session) -> Generator:
    yield session


@patch("app.messages.event.get_db")
def test_update_enterprise_event(mock_get: Mock, setup_db: Engine):
    # pylint: disable=redefined-outer-name,consider-using-dict-comprehension

    transaction = setup_db.connect()
    local_db_session = Session(autocommit=False, autoflush=False, bind=setup_db)

    saved_enterprise: Enterprise = Enterprise(
        name="testenterprise",
        accountable_email="testemail3@test.mail.com",
    )

    local_db_session.add(saved_enterprise)
    local_db_session.commit()
    local_db_session.refresh(saved_enterprise)

    assert saved_enterprise is not None
    assert saved_enterprise.id is not None

    mock_get.return_value = gen_db(local_db_session)

    # Arrange
    message = json.dumps(
        {
            "event_id": "UpdateEnterpise",
            "data": {
                "id": saved_enterprise.id,
                "name": "testenterprise2",
                "accountable_email": "testemail3@test.mail.com",
                "activity_type": "Test Activity other",
            },
            "start_date": datetime.datetime.now().isoformat(),
            "origin": "testorigin",
        }
    )

    local_db_session.close()
    # Act
    UpdateEvent.process_message(message)

    mock_get.assert_called()

    # Assert
    new_session = Session(autocommit=False, autoflush=False, bind=setup_db)

    with new_session:
        enterprise = new_session.exec(
            select(Enterprise).where(Enterprise.id == saved_enterprise.id)
        ).first()
        assert enterprise is not None
        assert enterprise.name == "testenterprise2"
        assert enterprise.activity_type == "Test Activity other"
        assert enterprise.accountable_email == "testemail3@test.mail.com"

    transaction.rollback()

    if new_session.is_active:
        new_session.close()

    if local_db_session.is_active:
        local_db_session.close()


@patch("app.messages.event.get_db")
def test_update_user_event(mock_get: Mock, setup_db: Engine):
    # pylint: disable=redefined-outer-name,consider-using-dict-comprehension

    transaction = setup_db.connect()
    local_db_session = Session(autocommit=False, autoflush=False, bind=setup_db)

    saved_enterprise: Enterprise = Enterprise(
        name="testenterprise",
        accountable_email="testemail3@test.mail.com",
    )

    saved_user: User = User(
        username="testuser",
        hashed_password="testpassword",
        email="testemail@test.mail.com",
        full_name="Test User",
        role_id=1,
        scope_id=1,
        enterprise_id=1,
    )

    local_db_session.add(saved_enterprise)
    local_db_session.commit()
    local_db_session.add(saved_user)
    local_db_session.commit()
    local_db_session.refresh(saved_user)

    assert saved_user is not None
    assert saved_user.id is not None

    mock_get.return_value = gen_db(local_db_session)

    # Arrange
    message = json.dumps(
        {
            "event_id": "UpdateUser",
            "data": {
                "user_id": saved_user.id,
                "username": "testuser2",
                "password": "testpassword2",
                "email": "emailtest2@test.com.br",
                "full_name": "Test User 2",
                "role_id": 1,
                "scope_id": 1,
                "enterprise_id": 1,
            },
            "start_date": datetime.datetime.now().isoformat(),
            "origin": "testorigin",
        }
    )

    local_db_session.close()
    # Act
    UpdateEvent.process_message(message)

    mock_get.assert_called_once()

    # Assert
    new_session = Session(autocommit=False, autoflush=False, bind=setup_db)

    with new_session:
        user = new_session.exec(select(User).where(User.id == saved_user.id)).first()
        assert user is not None
        assert user.username == "testuser2"
        assert user.email == "emailtest2@test.com.br"
        assert user.full_name == "Test User 2"
        assert user.role_id == 1
        assert user.scope_id == 1
        assert user.enterprise_id == 1

    transaction.rollback()

    if new_session.is_active:
        new_session.close()

    if local_db_session.is_active:
        local_db_session.close()
