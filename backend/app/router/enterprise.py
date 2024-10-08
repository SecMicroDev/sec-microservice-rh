"""Routes to manage enterprise resources, workers and roles."""

import json
from typing import Any, Callable, Coroutine

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.data_hash import get_hashed_data
from app.db.conn import get_db
from app.middlewares.auth import authenticate_user, authorize_user
from app.middlewares.send_message import get_async_message_sender_on_loop
from app.models.enterprise import (
    BaseEnterprise,
    Enterprise,
    EnterpriseRelation,
    EnterpriseResponse,
    EnterpriseUpdate,
    EnterpriseWithHierarchy,
)
from app.models.role import DefaultRole, DefaultRoleSchema, Role, RoleRelation
from app.models.scope import DefaultScope, DefaultScopeSchema, Scope, ScopeRelation
from app.models.user import FirstUserCreate, User, UserRead, UserResponse
from app.router.utils import (
    EnterpriseCreateEvent,
    EnterpriseDeleteEvent,
    EnterpriseDeleteWithId,
    EnterpriseUpdateEvent,
    EnterpriseUpdateWithId,
    UserCreateEvent,
)

router = APIRouter(prefix="/enterprise", tags=["Enterprise"])


def get_default_roles():
    return DefaultRoleSchema.get_default_roles().values()


def get_default_scopes():
    return DefaultScopeSchema.get_default_scopes().values()


def fill_roles_scopes(new_enterprise: Enterprise):
    for roleschema in get_default_roles():
        role = Role(**roleschema)
        if new_enterprise.roles is not None:
            new_enterprise.roles.append(role)
        else:
            new_enterprise.roles = [role]

    for scopeschema in get_default_scopes():
        scope = Scope(**scopeschema)
        if new_enterprise.scopes is not None:
            new_enterprise.scopes.append(scope)
        else:
            new_enterprise.scopes = [scope]

    return new_enterprise


def role_relation_from_enterprise(enterprise: Enterprise) -> list[RoleRelation]:
    if enterprise.roles is None:
        return []

    return list(map(lambda r: RoleRelation(**r.model_dump()), enterprise.roles))


def scope_relation_from_enterprise(enterprise: Enterprise) -> list[ScopeRelation]:
    if enterprise.scopes is None:
        return []
    return list(map(lambda s: ScopeRelation(**s.model_dump()), enterprise.scopes))


def get_filtered_roles(enterprise: Enterprise) -> Role | None:
    filtered_roles = list(
        filter(
            lambda x: x.name == DefaultRole.OWNER.value,
            (enterprise.roles if enterprise.roles is not None else []),
        )
    )

    return filtered_roles[0] if len(filtered_roles) > 0 else None


def get_filtered_scopes(enterprise: Enterprise) -> Scope | None:
    filtered_scopes = list(
        filter(
            lambda x: x.name == DefaultScope.ALL.value,
            (enterprise.scopes if enterprise.scopes is not None else []),
        )
    )
    return filtered_scopes[0] if len(filtered_scopes) > 0 else None


@router.post("/signup", response_model=UserResponse)
async def create_enterprise(
    enterprise: BaseEnterprise,
    user: FirstUserCreate,
    db_session: Session = Depends(get_db),
    send_message: Callable[[str], Coroutine[Any, Any, None]] = Depends(
        get_async_message_sender_on_loop
    ),
) -> UserResponse:
    """
    Create a new enterprise.

    Parameters:
        enterprise (EnterpriseCreate): The enterprise information to create.
        user (UserCreate): The user information to create.

    Returns:
        EnterpriseResponse: The response containing the created enterprise's information.
    """

    with db_session as session:
        # Create the enterprise
        new_enterprise = Enterprise(**enterprise.model_dump())
        new_enterprise = fill_roles_scopes(new_enterprise)

        default_role = get_filtered_roles(new_enterprise)
        default_scope = get_filtered_scopes(new_enterprise)

        if default_role is None or default_scope is None:
            raise HTTPException(
                status_code=500, detail="The default roles and scopes could not be set"
            )

        # Create the user
        new_user = User(
            **user.model_dump(exclude=set("password")),
            # enterprise_id=new_enterprise.id,
            # role_id=default_role.id,
            # scope_id=default_scope.id,
            hashed_password=get_hashed_data(user.password),
        )

        new_user.enterprise = new_enterprise
        new_user.role = default_role
        new_user.scope = default_scope

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        if (
            new_user is None
            or new_user.enterprise is None
            or new_user.role is None
            or new_user.scope is None
        ):
            raise HTTPException(
                status_code=500, detail="The enterprise could not be created"
            )

        user_read = UserRead(
            **new_user.model_dump(),
            enterprise=EnterpriseRelation(**new_user.enterprise.model_dump()),
            role=RoleRelation(**new_user.role.model_dump()),
            scope=ScopeRelation(**new_user.scope.model_dump()),
        )

        print(f"Signup User: {user_read.model_dump_json()}")

        await send_message(
            EnterpriseCreateEvent(
                data=EnterpriseWithHierarchy(
                    roles=role_relation_from_enterprise(new_user.enterprise),
                    scopes=scope_relation_from_enterprise(new_user.enterprise),
                    **new_user.enterprise.model_dump(),
                )
            ).model_dump_json()
        )

        await send_message(UserCreateEvent(data=user_read).model_dump_json())

        return UserResponse(
            status=200,
            message="Enterprise created",
            data=user_read,
        )


@router.get("/", response_model=EnterpriseResponse)
def get_enterprise(
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
) -> EnterpriseResponse:
    """
    Get your enterprise

    Parameters:
        enterprise_id (int): The ID of the enterprise to retrieve.

    Returns:
        EnterpriseResponse: The response containing the retrieved enterprise's information.
    """

    if identified_user is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    with db_session as session:
        enterprise = session.get(Enterprise, identified_user.enterprise_id)

        if enterprise is None:
            raise HTTPException(status_code=404, detail="Enterprise not found")

        return EnterpriseResponse(
            status=200,
            message="Enterprise retrieved",
            data=enterprise,
        )


@router.get("/full")
def get_full_enterprise(
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
) -> Response:
    """
    Get the full enterprise model if the user is an owner or manager.

    Parameters:
        db_session (Session): The database session.
        identified_user (UserRead): The authenticated user.

    Returns:
        EnterpriseResponse: The response containing the retrieved enterprise's information.
    """

    if identified_user is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    authorize_user(
        user=identified_user,
        operation_scopes=[DefaultScope.ALL.value, DefaultScope.HUMAN_RESOURCE.value],
        operation_hierarchy_order=(
            DefaultRole.get_default_hierarchy(DefaultRole.COLLABORATOR.value)
        ),
    )

    with db_session as session:
        enterprise = session.get(Enterprise, identified_user.enterprise_id)

        if (
            enterprise is None
            or enterprise.users is None
            or enterprise.roles is None
            or enterprise.scopes is None
        ):
            raise HTTPException(status_code=404, detail="Enterprise not found")

        resp = {
            "status": 200,
            "message": "Enterprise retrieved",
            "data": {
                "users": list(
                    map(
                        lambda user: json.loads(user.model_dump_json()),
                        enterprise.users,
                    )
                ),
                "roles": list(
                    map(
                        lambda role: json.loads(role.model_dump_json()),
                        enterprise.roles,
                    )
                ),
                "scopes": list(
                    map(
                        lambda scope: json.loads(scope.model_dump_json()),
                        enterprise.scopes,
                    )
                ),
                **enterprise.model_dump(),
            },
        }

        print("Enterprise Full:", str(resp))

        return Response(
            status_code=200,
            media_type="application/json",
            content=json.dumps(resp),
        )


@router.put("/", response_model=EnterpriseResponse)
async def update_enterprise(
    enterprise: EnterpriseUpdate,
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
    send_message: Callable[[str], Coroutine[Any, Any, None]] = Depends(
        get_async_message_sender_on_loop
    ),
) -> EnterpriseResponse:
    """
    Update an enterprise.

    Parameters:
        enterprise_id (int): The ID of the enterprise to update.
        enterprise (EnterpriseUpdate): The updated enterprise information.

    Returns:
        EnterpriseResponse: The response containing the updated enterprise's information.
    """

    if identified_user is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    authorize_user(
        user=identified_user,
        operation_scopes=[DefaultScope.ALL.value],
        operation_hierarchy_order=(
            DefaultRole.get_default_hierarchy(DefaultRole.OWNER.value)
        ),
    )

    with db_session as session:
        db_enterprise = session.get(Enterprise, identified_user.enterprise_id)

        if db_enterprise is None:
            raise HTTPException(status_code=404, detail="Enterprise not found")

        for key, value in enterprise.model_dump(exclude_none=True).items():
            if hasattr(db_enterprise, key):
                setattr(db_enterprise, key, value)
            else:
                raise HTTPException(status_code=400, detail=f"Invalid field: {key}")

        session.add(db_enterprise)
        session.commit()
        session.refresh(db_enterprise)

        if db_enterprise.id is not None:
            await send_message(
                EnterpriseUpdateEvent(
                    data=EnterpriseUpdateWithId(
                        id=db_enterprise.id,
                        **enterprise.model_dump(exclude_unset=True, exclude_none=True),
                    )
                ).model_dump_json(exclude_unset=True, exclude_none=True)
            )

            return EnterpriseResponse(
                status=200,
                message="Enterprise updated",
                data=EnterpriseRelation(
                    **db_enterprise.model_dump(),
                ),
            )

        raise HTTPException(
            status_code=500, detail="The enterprise could not be updated"
        )


@router.delete("/")
async def delete_enterprise(
    db_session: Session = Depends(get_db),
    identified_user: UserRead = Depends(authenticate_user),
    send_message: Callable[[str], Coroutine[Any, Any, None]] = Depends(
        get_async_message_sender_on_loop
    ),
) -> Response:
    """
    Delete an enterprise.

    Parameters:
        enterprise_id (int): The ID of the enterprise to delete.

    Returns:
        EnterpriseResponse: The response containing the confirmation message.
    """

    if identified_user is None:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    authorize_user(
        user=identified_user,
        operation_scopes=[DefaultScope.ALL.value],
        operation_hierarchy_order=(
            DefaultRole.get_default_hierarchy(DefaultRole.OWNER.value)
        ),
    )

    with db_session as session:
        db_enterprise = session.get(Enterprise, identified_user.enterprise_id)

        if db_enterprise is None:
            raise HTTPException(status_code=404, detail="Enterprise not found")

        session.delete(db_enterprise)
        session.commit()

        if identified_user.enterprise_id is None:
            raise HTTPException(
                status_code=500, detail="The enterprise could not be deleted"
            )

        await send_message(
            EnterpriseDeleteEvent(
                data=EnterpriseDeleteWithId(
                    id=identified_user.enterprise_id,
                )
            ).model_dump_json()
        )

        return Response(
            status_code=200,
            media_type="application/json",
            content=json.dumps({"message": "Enterprise deleted", "status": 200}),
        )
