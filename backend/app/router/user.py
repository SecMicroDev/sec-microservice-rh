"""
FastAPI router for handling User operations.

This module contains endpoints for creating, retrieving, updating, and deleting users.
"""

from collections.abc import Callable, Coroutine
from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, col, or_, and_, select
from sqlmodel.sql.expression import SelectOfScalar
from app.db.conn import get_db
from app.middlewares.send_message import get_async_message_sender_on_loop
from app.models.user import (
    User,
    UserCreate,
    UserListResponse,
    UserRead,
    UserResponse,
    UserUpdate,
    UserUpdateMe,
)
from app.auth.data_hash import get_hashed_data
from app.models.role import BaseRole, DefaultRole, Role, RoleRelation
from app.models.scope import BaseScope, DefaultScope, Scope, ScopeRelation
from app.models.enterprise import EnterpriseRelation
from app.middlewares.auth import authenticate_user, authorize_user
from .utils import (
    UserCreateEvent,
    UserDeleteEvent,
    UserDeleteWithId,
    UserUpdateEvent,
    UserUpdateWithId,
)


router = APIRouter(prefix="/users")


# def __create_event_message_resp(message: SQLModel) -> str:
#     return message.model_dump_json(exclude_unset=True)


def __retrieve_scope_role(
    user: UserCreate, identified_user: User, session: Session
) -> tuple[Scope | None, Role | None]:
    if user.scope_id and user.role_id:
        return __query_scope_role_by_id(
            user.role_id, user.scope_id, identified_user, session
        )
    elif user.scope_name and user.role_name:
        return __query_scope_role_by_name(
            user.role_name, user.scope_name, identified_user, session
        )

    return None, None


def __query_scope_role_by_id(
    role_id: int, scope_id: int, identified_user: User, db_session: Session
) -> tuple[Scope | None, Role | None]:

    scope: Scope | None = None
    role: Role | None = None

    # scope_full: Scope | None = None
    # role_full: Role | None = None

    res = db_session.exec(
        identified_user.query_scope_role_by_id(role_id, scope_id)
    ).first()

    if res:
        _, scope, role = res

    # if scope_full and role_full:
    # scope = ScopeRead(**scope_full.model_dump())
    # role = RoleRead(**role_full.model_dump())

    return scope, role


def __query_scope_role_by_name(
    role_name: str, scope_name: str, identified_user: User, db_session: Session
) -> tuple[Scope | None, Role | None]:

    scope: Scope | None = None
    role: Role | None = None

    res = db_session.exec(
        identified_user.query_scope_role_by_name(role_name, scope_name)
    ).first()

    if res:
        _, scope, role = res

    # if scope_full is not None and role_full is not None:
    #     scope = ScopeRead(**scope_full.model_dump())
    #     role = RoleRead(**role_full.model_dump())

    return scope, role


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user: UserCreate,
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
    send_message: Callable[[str], Coroutine] = Depends(
        get_async_message_sender_on_loop
    ),
) -> UserResponse:
    """
    Create a new user.

    Parameters:
        user (User): The user to create.

    Returns:
        dict: Confirmation message and user_id of the created user.
    """

    if identified_user is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    with db_session as session:
        id_user = session.get(User, identified_user.id)

        if id_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        scope, role = __retrieve_scope_role(user, id_user, session)

        if not scope or not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Scope or Role for the Enterprise",
            )

        authorized_user = authorize_user(
            user=identified_user,
            operation_scopes=[scope.name],
            operation_hierarchy_order=role.hierarchy,
        )
        if not (authorized_user is None):
            try:
                user.scope_id = scope.id
                user.role_id = role.id
                userschema = user.model_dump()
                passwd = userschema.pop("password")
                userschema["created_at"] = datetime.now()
                db_user = User(**userschema, hashed_password=get_hashed_data(passwd))
                session.add(db_user)

                session.commit()
                session.refresh(db_user)

                if not db_user.role or not db_user.scope or not db_user.enterprise:
                    raise HTTPException(status_code=500, detail="User creation failed")

                print(
                    "User created: ",
                    db_user.username,
                    db_user.role.name,
                    db_user.scope.name,
                    db_user.enterprise.name,
                )

                role = RoleRelation(**db_user.role.model_dump())
                scope = ScopeRelation(**db_user.scope.model_dump())
                enterprise = EnterpriseRelation(**db_user.enterprise.model_dump())

                user_read = UserRead(
                    **db_user.model_dump(),
                    role=role,
                    scope=scope,
                    enterprise=enterprise,
                )

                await send_message(
                    UserCreateEvent(
                        data=user_read, event_scope=user_read.scope.name
                    ).model_dump_json()
                )

                return UserResponse(
                    status=201,
                    message="User created",
                    data=user_read,
                )

            except Exception as exc:
                print(exc)
                raise HTTPException(status_code=500, detail="Unknown error") from exc

        else:
            raise HTTPException(status_code=403, detail="Unauthorized user")


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: UserRead = Depends(authenticate_user),
) -> UserResponse:
    """
    Get the current authenticated user.

    Parameters:
        current_user (UserRead): The authenticated user.

    Returns:
        UserResponse: The response containing the current user's information.
    """

    if not (current_user is None):
        return UserResponse(
            status=200,
            message="Current user retrieved",
            data=current_user,
        )
    else:
        raise HTTPException(status_code=404, detail="User not found")


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user: UserUpdateMe,
    current_user: UserRead = Depends(authenticate_user),
    db_session: Session = Depends(get_db),
    send_message: Callable[[str], Coroutine] = Depends(
        get_async_message_sender_on_loop
    ),
) -> UserResponse:
    """
    Update the current authenticated user.

    Parameters:
        user (User): The updated user information.
        current_user (UserRead): The authenticated user.

    Returns:
        UserResponse: The response containing the updated user's information.
    """
    resp: UserResponse | None = None

    if not (current_user is None):
        with db_session as session:
            print("User identified for UPDATE: ", current_user.id)

            from_db = session.get(User, current_user.id)

            if from_db is None:
                raise HTTPException(status_code=404, detail="User not found")

            if user.password:
                hashed_password = get_hashed_data(user.password)
                from_db.hashed_password = hashed_password

            if user.username:
                from_db.username = user.username

            if user.email:
                from_db.email = user.email

            if user.full_name:
                from_db.full_name = user.full_name

            session.add(from_db)
            session.commit()
            session.refresh(from_db)

            if not from_db.role or not from_db.scope or not from_db.enterprise:
                raise HTTPException(status_code=500, detail="User creation failed")

            user_read = UserRead(
                **from_db.model_dump(),
                role=RoleRelation(**from_db.role.model_dump()),
                scope=ScopeRelation(**from_db.scope.model_dump()),
                enterprise=EnterpriseRelation(**from_db.enterprise.model_dump()),
            )

            resp = UserResponse(
                status=200,
                message="Current user updated",
                data=user_read,
            )

            if any([k != "password" for k, _ in user.model_dump().items()]):

                await send_message(
                    UserUpdateEvent(
                        event_scope=user_read.scope.name,
                        update_scope=user_read.scope.name,
                        user=user_read,
                        data=UserUpdateWithId(
                            id=user_read.id,
                            enterprise_id=user_read.enterprise.id,
                            **UserUpdate(**user_read.model_dump()).model_dump(
                                exclude_none=True
                            ),
                        ),
                    ).model_dump_json()
                )

            return resp
    else:
        print(
            f'User not found None={current_user is None} ID={current_user.id if current_user.id is not None else ""}',
            current_user,
        )
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
) -> UserResponse:
    """
    Get a user by their ID.

    Parameters:
        user_id (int): The ID of the user to retrieve.

    Returns:
        UserResponse: The response containing the user's information.
    """

    if identified_user is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    with db_session as session:
        user = session.exec(
            select(User)
            .where(col(User.id) == user_id)
            .where(col(User.enterprise_id) == identified_user.enterprise_id)
        ).first()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.role or not user.scope or not user.enterprise:
            raise HTTPException(status_code=500, detail="User creation failed")

        authorize_user(
            user=identified_user,
            operation_scopes=[user.scope.name],
            operation_hierarchy_order=user.role.hierarchy,
        )

        role = RoleRelation(**user.role.model_dump())
        scope = ScopeRelation(**user.scope.model_dump())
        enterprise = EnterpriseRelation(**user.enterprise.model_dump())

    return UserResponse(
        status=200,
        message="User retrieved",
        data=UserRead(
            **user.model_dump(), role=role, scope=scope, enterprise=enterprise
        ),
    )


@router.get("/", response_model=UserListResponse)
async def get_all_users(
    scope_names: str | None = None,
    scope_ids: str | None = None,
    role_names: str | None = None,
    role_ids: str | None = None,
    usernames: str | None = None,
    emails: str | None = None,
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
) -> UserListResponse:
    """
    Get all users.

    Returns:
        UserResponse: The response containing the list of users.
    """

    query_scope: SelectOfScalar | None = None
    query_role: SelectOfScalar | None = None

    if identified_user is None or identified_user.enterprise_id is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    if scope_ids:
        scopes_to_search = map(int, scope_ids.split(","))
        query_scope = BaseScope.get_scopes_by_ids(
            identified_user.enterprise_id, list(scopes_to_search)
        )
    elif scope_names:
        scopes_to_search = scope_names.split(",")
        query_scope = BaseScope.get_scopes_by_names(
            identified_user.enterprise_id, scopes_to_search
        )

    if role_ids:
        roles_to_search = map(int, role_ids.split(","))
        query_role = BaseRole.get_roles_by_ids(
            identified_user.enterprise_id, list(roles_to_search)
        )
    elif role_names:
        roles_to_search = role_names.split(",")
        query_role = BaseRole.get_roles_by_names(
            identified_user.enterprise_id, roles_to_search
        )

    with db_session as session:
        roles = session.exec(query_role).all() if not (query_role is None) else None
        scopes = session.exec(query_scope).all() if not (query_scope is None) else None
        id_user = session.get(User, identified_user.id)

        if id_user is None:
            raise HTTPException(status_code=404, detail="User not found for auth token")

        if (not (query_role is None) and roles is None) or (
            not (query_scope is None) and scopes is None
        ):
            raise HTTPException(
                status_code=404, detail="Roles and Scopes not found for this enterprise"
            )

        query: SelectOfScalar | None = None

        query = id_user.get_all()

        if roles or scopes:
            print("Scopes to search", scopes)
            print("Roles to search", roles)
            res = session.exec(
                identified_user.query_scopes_roles(
                    list(map(lambda x: x.id, roles if roles else [])),
                    list(map(lambda x: x.id, scopes if scopes else [])),
                )
            ).all()

            if res is None or len(res) < 0:
                print(f"Scopes and roles filter {res}")
                raise HTTPException(
                    status_code=404,
                    detail="Roles and Scopes not found for this enterprise",
                )

            for r in res:
                _, result_scope, result_role = r

                if result_scope is not None:
                    query = query.where(
                        and_(User.role_id == result_role.id)
                        # .in_(list(map(lambda x: x.id, result_role)))
                    )

                if result_role is not None:
                    query = query.where(
                        and_(User.scope_id == result_scope.id)
                        # .in_(list(map(lambda x: x.id, result_scopes)))
                    )

        if usernames:
            query = query.where(
                or_(
                    *[
                        col(User.username).regexp_match(name)
                        for name in map(lambda x: str(x).strip(), usernames.split(","))
                    ]
                )
            )

        if emails:
            query = query.where(
                or_(
                    *[
                        col(User.email).regexp_match(email)
                        for email in map(lambda x: str(x).strip(), emails.split(","))
                    ]
                )
            )

        users = session.exec(query).all()

        if users is None:
            raise HTTPException(status_code=404, detail="Users not found")

        authorized_user = authorize_user(
            user=identified_user,
            operation_scopes=[DefaultScope.ALL.value],
            operation_hierarchy_order=(
                DefaultRole.get_default_hierarchy(DefaultRole.OWNER.value)
            ),
        )

        if authorized_user:
            user_list: list[UserRead] = []
            count = 0
            for user in users:
                print(f"User {count}", str(user.model_dump()))
                count += 1

                role = RoleRelation(**user.role.model_dump())
                scope = ScopeRelation(**user.scope.model_dump())
                enterprise = EnterpriseRelation(**user.enterprise.model_dump())

                user_list.append(
                    UserRead(
                        **user.model_dump(),
                        role=role,
                        scope=scope,
                        enterprise=enterprise,
                    )
                )

            return UserListResponse(
                status=200,
                message="Users retrieved",
                data=user_list,
            )

        else:
            raise HTTPException(status_code=403, detail="Unauthorized user")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user: UserUpdate,
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
    send_message: Callable[[str], Coroutine] = Depends(
        get_async_message_sender_on_loop
    ),
) -> UserResponse:
    """
    Update a user.

    Parameters:
        user_id (int): The ID of the user to update.
        user (User): The updated user information.

    Returns:
        UserResponse: The response containing the updated user's information.
    """

    role: Role | None = None
    scope: Scope | None = None

    if identified_user is None or identified_user.enterprise_id is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    with db_session as session:
        old_scope: Scope | None = None

        if user.role_id:
            role = session.get(Role, user.role_id)
            if role is None:
                raise HTTPException(status_code=404, detail="Role not found")
        elif user.role_name:
            role = session.exec(
                BaseRole.get_roles_by_names(
                    identified_user.enterprise_id, [user.role_name]
                )
            ).first()
            if role is None:
                raise HTTPException(status_code=404, detail="Role not found")

        if user.scope_id:
            scope = session.get(Scope, user.scope_id)
            if scope is None:
                raise HTTPException(status_code=404, detail="Scope not found")
        elif user.scope_name:
            scope = session.exec(
                BaseScope.get_roles_by_names(
                    identified_user.enterprise_id, [user.scope_name]
                )
            ).first()
            if scope is None:
                raise HTTPException(status_code=404, detail="Scope not found")

        db_user: User | None = session.exec(
            select(User)
            .where(User.id == user_id)
            .where(User.enterprise_id == identified_user.enterprise_id)
        ).first()

        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if db_user.enterprise is None or db_user.scope is None or db_user.role is None:
            raise HTTPException(status_code=500, detail="User creation failed")

        if identified_user.scope is None or identified_user.role is None:
            raise HTTPException(status_code=403, detail="Unauthorized user")

        authorize_user(
            user=identified_user,
            operation_scopes=[db_user.scope.name],
            operation_hierarchy_order=min(
                db_user.role.hierarchy, role.hierarchy if role else int(2**30 - 1)
            ),
            custom_checks=(
                db_user.scope.name == identified_user.scope.name
                and (scope.name == identified_user.scope.name if scope else True)
            ),
        )

        if role:
            db_user.role_id = role.id
            db_user.role = role

        if scope:
            old_scope = db_user.scope
            db_user.scope_id = scope.id
            db_user.scope = scope

        if user.password:
            db_user.hashed_password = get_hashed_data(user.password)

        if user.username:
            db_user.username = user.username

        if user.email:
            db_user.email = user.email

        if user.full_name:
            db_user.full_name = user.full_name

        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        if db_user.role is None or db_user.scope is None or db_user.enterprise is None:
            raise HTTPException(status_code=500, detail="User creation failed")

        enterprise = EnterpriseRelation(**db_user.enterprise.model_dump())
        role_rel = RoleRelation(**db_user.role.model_dump())
        scope_rel = ScopeRelation(**db_user.scope.model_dump())

        user_read = UserRead(
            **db_user.model_dump(),
            role=role_rel,
            scope=scope_rel,
            enterprise=enterprise,
        )

        if any([k != "password" for k, _ in user.model_dump().items()]):

            await send_message(
                UserUpdateEvent(
                    event_scope=(
                        user_read.scope.name if old_scope is None else old_scope.name
                    ),
                    update_scope=user_read.scope.name,
                    user=user_read,
                    data=UserUpdateWithId(
                        id=user_read.id,
                        enterprise_id=user_read.enterprise.id,
                        **UserUpdate(
                            **user_read.model_dump(exclude_none=True)
                        ).model_dump(),
                    ),
                ).model_dump_json()
            )

        return UserResponse(
            status=200,
            message="User updated",
            data=user_read,
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
    send_message: Callable[[str], Coroutine] = Depends(
        get_async_message_sender_on_loop
    ),
) -> Response:
    """
    Delete a user.

    Parameters:
        user_id (int): The ID of the user to delete.

    Returns:
        UserResponse: The response containing the confirmation message.
    """

    if identified_user is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    with db_session as session:
        db_user: User | None = session.exec(
            select(User)
            .where(User.id == user_id)
            .where(User.enterprise_id == identified_user.enterprise_id)
        ).first()

        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if db_user.enterprise is None or db_user.scope is None or db_user.role is None:
            raise HTTPException(status_code=500, detail="User creation failed")

        authorize_user(
            user=identified_user,
            operation_scopes=[db_user.scope.name],
            operation_hierarchy_order=db_user.role.hierarchy,
        )

        session.delete(db_user)
        session.commit()

        if identified_user.enterprise_id is None:
            raise HTTPException(status_code=500, detail="User deletion failed")

        await send_message(
            UserDeleteEvent(
                event_scope=db_user.scope.name,
                data=UserDeleteWithId(
                    id=user_id, enterprise_id=identified_user.enterprise_id
                ),
            ).model_dump_json()
        )

    return Response(
        status_code=200,
        content=json.dumps(dict(status=200, message="User deleted")),
        media_type="application/json",
    )
