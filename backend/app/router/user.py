"""
FastAPI router for handling User operations.

This module contains endpoints for creating, retrieving, updating, and deleting users.
"""

from fastapi import APIRouter, HTTPException
from app.db.conn import SessionLocal
from app.models.user import User

router = APIRouter(prefix="/users")


@router.post("/")
async def create_user(user: User):
    """
    Create a new user.

    Parameters:
        user (User): The user to create.

    Returns:
        dict: Confirmation message and user_id of the created user.
    """

    try:

        session = SessionLocal()

        db_user = User(**user.model_dump())
        session.add(db_user)

        session.commit()
        user_id = db_user.id

        session.close()

        return {"message": "User created successfully", "user_id": user_id}

    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unknown error") from exc
