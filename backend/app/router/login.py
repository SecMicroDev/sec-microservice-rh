import json
from sqlmodel import SQLModel, Session, select
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.data_hash import validate_hashed_data
from app.auth.jwt_utils import create_jwt_token
from app.db.conn import get_db
from app.models.user import User, UserRead


class Token(SQLModel):
    access_token: str
    token_type: str


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
async def login_for_access_token(
    login_req: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):

    with db as session:
        user = session.exec(
            select(User).where(User.email == login_req.username)
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect username or password",
            )

        validated_pass = validate_hashed_data(login_req.password, user.hashed_password)

        if not validated_pass:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        access_token = create_jwt_token(
            json.loads(
                UserRead(
                    **user.model_dump(),
                    enterprise=user.enterprise,
                    scope=user.scope,
                    role=user.role
                ).model_dump_json(exclude_none=True, exclude_unset=True)
            )
        )

        return {"access_token": access_token, "token_type": "bearer"}
