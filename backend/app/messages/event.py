import datetime
import json
from typing import Any

from sqlmodel import Session

from app.db.conn import get_db
from app.models.enterprise import Enterprise, EnterpriseUpdate
from app.models.user import User, UserUpdate
from app.auth.data_hash import get_hashed_data
from app.models.role import BaseRole, Role
from app.models.scope import BaseScope, Scope


class UpdateEvent:
    def __init__(
        self,
        event_id: str,
        data: dict[str, Any],
        start_date: datetime.datetime,
        origin: str,
    ):

        self.event_id = event_id
        self.data = data
        self.start_date = start_date
        self.origin = origin

    @classmethod
    def create_from_message(cls, message: str):
        message_dict = json.loads(message)

        return cls(
            message_dict["event_id"],
            message_dict["data"],
            datetime.datetime.fromisoformat(message_dict["start_date"]),
            message_dict["origin"],
        )

    @classmethod
    def process_message(cls, message: str):
        event = cls.create_from_message(message)
        event.update_table()

    def update_table(self):
        if self.event_id == "UpdateEnterpise":
            print("Received UpdateEnterpise event")
            self.update_enterprise()
        if self.event_id == "UpdateUser":
            print("Received UpdateUser event")
            self.update_user()

    def update_enterprise(self):
        db: Session | None = None
        print(f"Start enterprise update: Data -- {self.data}")
        try:
            db = next(get_db())
            with db as session:
                enterprise_update = EnterpriseUpdate(**self.data)
                enterprise = session.get(Enterprise, self.data["id"])

                if enterprise is not None:

                    for key, value in enterprise_update.model_dump().items():
                        if hasattr(enterprise, key):
                            print(f"Setting {key} to {value}")
                            setattr(enterprise, key, value)

                    print("Updating enterprise...")
                    session.add(enterprise)
                    session.commit()

                else:
                    print(f'Enterprise with id {self.data["id"]} not found')
        except Exception as e:
            print("Messaging error: ", e.__str__())
            if db:
                db.rollback()
                db.close()

    def update_user(self):
        db: Session | None = None
        role: Role | None = None
        scope: Scope | None = None
        print(f"Start User update: Data -- {self.data}")
        try:
            if self.data["enterprise_id"] and self.data["user_id"]:

                print("Parsed enterprise and user data...")
                db = next(get_db())

                with db as session:
                    print("Interacting with the database...")

                    if self.data["role_id"]:
                        role = session.get(Role, self.data["role_id"])
                    elif "role_name" in self.data:
                        role = session.exec(
                            BaseRole.get_roles_by_names(
                                self.data["enterprise_id"], [self.data["role_name"]]
                            )
                        ).first()

                    if "scope_id" in self.data:
                        scope = session.get(Scope, self.data["scope_id"])
                    elif "scope_name" in self.data:
                        scope = session.exec(
                            BaseScope.get_roles_by_names(
                                self.data["enterprise_id"], [self.data["scope_name"]]
                            )
                        ).first()

                    print("finding user...")
                    db_user = session.get(User, self.data["user_id"])

                    if db_user:

                        if role:
                            db_user.role_id = role.id
                            db_user.role = role

                        if scope is not None:
                            db_user.scope_id = scope.id
                            db_user.scope = scope

                        if "password" in self.data:
                            db_user.hashed_password = get_hashed_data(
                                self.data["password"]
                            )

                        if "username" in self.data:
                            db_user.username = self.data["username"]

                        if "email" in self.data:
                            db_user.email = self.data["email"]

                        if "full_name" in self.data:
                            db_user.full_name = self.data["full_name"]

                        print("Updating user...")
                        session.add(db_user)
                        session.commit()

                    else:
                        print(f'User with id {self.data["user_id"]} not found')

        except Exception as e:
            print("Messaging Error :", e.__str__())
            if db:
                db.rollback()
                db.close()
