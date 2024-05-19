"""  User model package """

from typing import TYPE_CHECKING, Optional
from datetime import datetime as dt
from pydantic import EmailStr
from sqlalchemy import String
from sqlmodel import Field, Relationship, SQLModel, Column

from app.models.enterprise import Enterprise
from app.db.base import BaseIDModel

from app.models.role import Role
from app.models.scope import Scope
from app.models.api_response import APIResponse

if TYPE_CHECKING:
    from app.models.role import RoleRelation
    from app.models.scope import ScopeRelation


class BaseUser(SQLModel):
    """Represents a user stored in the database."""

    username: str = Field(
        description="Username for the user.",
        sa_column=Column(String, index=True, unique=True),
    )
    email: EmailStr = Field(
        sa_column=Column(String, unique=True, index=True),
        description="Email address of the user.",
    )
    full_name: Optional[str] = Field(
        default=None, description="Full name of the user.", nullable=True
    )


class User(BaseIDModel, BaseUser, table=True):
    """
    Represents a user in the system.

    Attributes:
        hashed_password (str): Hashed password for the user.
        created_at (datetime): Timestamp of when the user was registered.
        role_id (int, optional): ID of the role associated with the user.
        scope_id (int, optional): ID of the scope associated with the user.
        enterprise_id (int, optional): ID of the enterprise associated with the user.
        role (Role, optional): Role object associated with the user.
        scope (Scope, optional): Scope object associated with the user.
        enterprise (Enterprise, optional): Enterprise object associated with the user.
    """
    
    __tablename__ = "user"
    hashed_password: str = Field(
        description="Hashed password for the user.",
    )
    created_at: dt = Field(
        description="Timestamp of when the user was registered.",
        default_factory=dt.now,
    )
    role_id: Optional[int] = Field(default=None, foreign_key="role.id")
    scope_id: Optional[int] = Field(
        default=None, foreign_key="scope.id", nullable=False
    )
    enterprise_id: Optional[int] = Field(foreign_key="enterprise.id", nullable=False)
    role: Optional[Role] = Relationship(back_populates="users")
    scope: Optional[Scope] = Relationship(back_populates="users")
    enterprise: Optional[Enterprise] = Relationship(back_populates="users")


class UserCreate(BaseUser):
    """Represents a user creation request."""

    password: str
    enterprise_id: int 
    role_id: Optional[int] = None
    scope_id: Optional[int] = None
    role_name: Optional[str] = None
    scope_name: Optional[str] = None


class UserRead(BaseUser):
    """Represents a user read response."""

    created_at: dt
    edited_at: Optional[dt] = None
    role: "RoleRelation"
    scope: "ScopeRelation"
    enterprise: Enterprise


class UserUpdate(UserCreate):
    """Represents a user update request."""

    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    hashed_password: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    scope_name: Optional[str] = None
    scope_id: Optional[int] = None


class UserListResponse(APIResponse):
    """Represents a list of users."""

    data: list[UserRead] = []


class UserResponse(APIResponse):
    """Represents a user response."""

    data: UserRead
