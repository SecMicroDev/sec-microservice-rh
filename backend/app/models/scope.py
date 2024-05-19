"""
This module defines the Scope model for storing scopes in the database.

The Scope model inherits from the BaseIDModel and BaseScope classes, which provide common fields and functionality.
It represents a scope stored in the database.

Attributes:
    name (str): The name of the scope.
    description (Optional[str]): The description of the scope.

"""

from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional, Union
from sqlalchemy import Column, String
from sqlmodel import Field, Relationship, SQLModel

import uuid as uuid_pkg

from app.db.base import BaseIDModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.enterprise import Enterprise


class BaseScope(SQLModel):
    """Represents a basic scope"""

    name: str = Field(
        description="Name of the scope.",
        sa_column=Column(String, unique=True, index=True, nullable=False),
    )
    description: Optional[str] = Field(
        description="Description of the scope.", nullable=True
    )
    enterprise_id: int = Field(
        foreign_key="enterprise.id",
        description="The enterprise to which the scope belongs.",
        nullable=True,
    )


class Scope(BaseIDModel, BaseScope, table=True):
    """Represents a scope stored in the database."""

    __tablename__ = "scope"
    users: list["User"] = Relationship(back_populates="scope")
    enterprise: "Enterprise" = Relationship(back_populates="scopes")

    # @declared_attr
    # def scope_id(self):
    #     return synonym("id")


class ScopeRead(SQLModel):
    """Represents a scope read response."""

    id: int
    name: str


class ScopeCreate(BaseScope):
    """Represents a scope creation request."""

    pass


class ScopeUpdate(SQLModel):
    """Represents a scope update request."""

    name: Optional[str] = None
    description: Optional[str] = None


class DefaultScope(str, Enum):
    SELLS = "Sells"
    HUMAN_RESOURCE = "HumanResource"
    PATRIMONIAL = "Patrimonial"


class DefaultScopeSchema(SQLModel):
    name: DefaultScope
    description: str

    @classmethod
    def get_default_scopes(cls) -> dict[
        Union[Literal[DefaultScope.SELLS],
                Literal[DefaultScope.HUMAN_RESOURCE],
                Literal[DefaultScope.PATRIMONIAL]],
        dict[str, str]
    ]:
        return {
            DefaultScope.SELLS: dict(name=DefaultScope.SELLS, description="Sells scope from the enterprise."),
            DefaultScope.HUMAN_RESOURCE: dict(name=DefaultScope.HUMAN_RESOURCE, description="Human resource from the enterprise."),
            DefaultScope.PATRIMONIAL: dict(name=DefaultScope.PATRIMONIAL, description="Patrimonial scope from the enterprise."),
        }


class ScopeRelation(SQLModel):
    """Represents a scope in the User model."""

    id: Optional[int] = None
    name: str
