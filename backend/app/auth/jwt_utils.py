"""
Create, sign and verify JWT Tokens
"""

from datetime import datetime, timedelta
from typing import Any, Union
from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import JWKError, JWSSignatureError, JWTClaimsError
from app.auth.settings import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY, ALGORITHM

import json

DEFAULT_OPTIONS = {
    "iss": "openferp.org",
}


class JWTValidationError(Exception):
    def __init__(self):
        super().__init__("JWTValidationError: ")


def create_jwt_token(
    payload: dict,
    expires: int = ACCESS_TOKEN_EXPIRE_MINUTES,
    config: dict[str, str] = {"JWT_KEY": JWT_SECRET_KEY, "JWT_ALGO": ALGORITHM},
) -> str:
    """
    Create a signed token with a defined algorithm and secret
    for signature. The payload is a dict and the expire time is in minutes
    """

    current_default_options: dict[str, Union[str, datetime]] = {
        **DEFAULT_OPTIONS,
        "iat": datetime.now(),
    }

    return jwt.encode(
        {
            "exp": (datetime.now() + timedelta(seconds=expires)).timestamp(),
            "sub": str(payload).replace("'", '"'),
            **current_default_options,
        },
        config["JWT_KEY"],
        config["JWT_ALGO"],
    )


def decode_jwt_token(
    token: str,
    config: dict[str, Any] = {"JWT_KEY": JWT_SECRET_KEY, "JWT_ALGO": ALGORITHM},
) -> Union[dict[str, Any], None]:
    """
    Decode a signed token with a defined algorithm and secret
    for signature. The payload is a dict and the expire time is in minutes
    """

    decoded_claims: Union[dict[str, Any], None] = None

    decoded_claims = jwt.decode(
        token,
        key=config["JWT_KEY"],
        algorithms=config["JWT_ALGO"],
        issuer=DEFAULT_OPTIONS["iss"],
    )

    decoded_claims.update(dict(sub=json.loads(decoded_claims["sub"])))

    if abs(
        (datetime.fromtimestamp(decoded_claims["exp"]) - datetime.now())
    ) <= timedelta(0):
        raise JWTClaimsError("Invalid exp time")

    return decoded_claims


def get_user_data(token: str) -> dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_jwt_token(token)
        user_data: str = payload.get("sub")
        if user_data is None:
            raise credentials_exception
    except JWTValidationError:
        raise credentials_exception

    return user_data
