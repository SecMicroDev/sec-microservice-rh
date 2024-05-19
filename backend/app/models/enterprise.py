from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import BaseIDModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.role import Role
    from app.models.scope import Scope


class BaseEnterprise(SQLModel):
    """Represents a basic enterprise."""

    name: str = Field(description="Name of the enterprise.")
    accountable_email: str = Field(
        description="Email of the person accountable for the organization."
    )
    activity_type: str = Field(
        default="Others", description="Activity type of the enterprise."
    )


class Enterprise(BaseIDModel, BaseEnterprise, table=True):
    """Represents an enterprise."""

    __tablename__ = "enterprise"
    users: Optional[list["User"]] = Relationship(back_populates="enterprise")
    scopes: Optional[list["Scope"]] = Relationship(back_populates="enterprise")
    roles: Optional[list["Role"]] = Relationship(back_populates="enterprise")
