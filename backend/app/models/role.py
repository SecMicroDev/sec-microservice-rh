"""
This module defines the Role model and its base class.
"""

from typing import TYPE_CHECKING, Literal, Optional, Union
from sqlalchemy import Column, String
from sqlmodel import Field, Relationship, SQLModel


from app.db.base import BaseIDModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.enterprise import Enterprise
from enum import Enum


class BaseRole(SQLModel):
    """Represents a role stored in the database."""

    name: str = Field(
        description="Name of the role.",
        sa_column=Column(String, unique=True, index=True, nullable=False),
    )
    description: Optional[str] = Field(
        description="Description of the role.", nullable=True
    )
    hierarchy: int = Field(nullable=False)
    enterprise_id: int = Field(
        foreign_key="enterprise.id",
        description="The enterprise to which the scope belongs.",
        nullable=True,
    )


class Role(BaseIDModel, BaseRole, table=True):
    """Represents a role stored in the database."""

    __tablename__ = "role"
    users: list["User"] = Relationship(back_populates="role")
    enterprise: "Enterprise" = Relationship(back_populates="roles")



class RoleCreate(BaseRole):
    """Represents a role creation request."""

    pass


class RoleRead(BaseRole):
    """Represents a role read response."""

    pass


class DefaultRole(str, Enum):
    OWNER = "Owner"
    MANAGER = "Manager"
    COLLABORATOR = "Collaborator"


class DefaultRoleSchema(SQLModel):
    name: DefaultRole
    description: str

    @classmethod
    def get_default_roles(cls) -> dict[
        Union[Literal[DefaultRole.OWNER],
              Literal[DefaultRole.COLLABORATOR],
              Literal[DefaultRole.MANAGER]],
        dict[str, str]
    ]:
        return {
            DefaultRole.OWNER: dict(name=DefaultRole.OWNER, description="The owner of the enterprise.", hierarchy=1),
            DefaultRole.COLLABORATOR: dict(name=DefaultRole.COLLABORATOR, description="A collaborator of the enterprise.", hierarchy=3),
            DefaultRole.MANAGER: dict(name=DefaultRole.MANAGER, description="A manager of the enterprise.", hierarchy=2),
        }


class RoleUpdate(SQLModel):
    """Represents a role update request."""

    name: Optional[str] = None
    description: Optional[str] = None
    hierarchy: Optional[int] = None


class RoleRelation(SQLModel):
    """Represents the role in a User model."""

    id: Optional[int] = None
    name: str
    hierarchy: int
