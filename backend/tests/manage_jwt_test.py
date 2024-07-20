import base64
from datetime import datetime, timedelta
import json

import jwt
from jwt import ExpiredSignatureError
import pytest

from app.auth.jwt_utils import DEFAULT_OPTIONS, create_jwt_token, decode_jwt_token
import app.auth.settings as st


DEFAULT_DOMAIN_KEYS = ["user", "role", "id"]
DEFAULT_JWT_KEYS = ["exp", "iss", "iat", "sub"]


def get_default_data() -> tuple[dict[str, str], int, dict[str, str]]:
    """
    Get default test_data
    """

    return (
        {
            "JWT_KEY": base64.b64encode("testunsafeinsecurekey".encode("ascii")).decode(
                "ascii"
            ),
            "JWT_ALGO": "HS256",
        },
        30,
        {"user": "fake_user", "role": "Supervisor", "id": "abcdef123456"},
    )


def test_correct_jwt_creation():
    """
    Test jwt token creation
    """

    config, expire_min, val = get_default_data()

    default_options = {
        **DEFAULT_OPTIONS,
        "iat": datetime.now().timestamp(),
    }

    hashed = create_jwt_token(val, expire_min, config)
    claims_resp = jwt.decode(hashed, options={"verify_signature": False})

    assert all(k in claims_resp for k in ["exp", "iss", "iat", "sub"])

    valid_time = (datetime.now() + timedelta(minutes=expire_min)).timestamp()

    decoded = jwt.decode(hashed, config["JWT_KEY"], algorithms=[config["JWT_ALGO"]])

    assert {k: decoded.get(k, json.loads(decoded["sub"])[k]) for k in val} == val

    assert (
        jwt.decode(hashed, options={"verify_signature": False})["exp"] - valid_time
    ) <= 2

    for k in DEFAULT_OPTIONS:
        assert claims_resp[k] == default_options[k]

    for k, v in val.items():
        if k in claims_resp:
            assert claims_resp[k] == v
        else:
            assert json.loads(claims_resp["sub"])[k] == v


def test_correct_jwt_creation_with_defaults():
    """
    Test jwt token creation with defaults
    """

    _, expire_min, val = get_default_data()

    default_options = {
        **DEFAULT_OPTIONS,
        "iat": datetime.now().timestamp(),
    }

    hashed = create_jwt_token(val, expire_min)
    claims_resp = jwt.decode(hashed, options={"verify_signature": False})

    assert all(k in claims_resp for k in ["exp", "iss", "iat", "sub"])

    valid_time = (datetime.now() + timedelta(minutes=expire_min)).timestamp()

    decoded = jwt.decode(hashed, st.JWT_SECRET_DECODE_KEY, algorithms=[st.ALGORITHM])

    assert {k: decoded.get(k, json.loads(decoded["sub"])[k]) for k in val} == val

    assert (
        jwt.decode(hashed, options={"verify_signature": False})["exp"] - valid_time
    ) <= 2

    for k in DEFAULT_OPTIONS:
        assert claims_resp[k] == default_options[k]

    for k, v in val.items():
        if k in claims_resp:
            assert claims_resp[k] == v
        else:
            assert json.loads(claims_resp["sub"])[k] == v


def test_correct_jwt_parsing():
    """
    Test correct parsing with defaults
    """

    _, expire_min, val = get_default_data()
    print(*get_default_data())
    valid_time = datetime.now() + timedelta(minutes=expire_min)
    hashed = create_jwt_token(val, expire_min)

    # print(jws.verify(hashed, config['JWT_KEY'], algorithms=config['JWT_ALGO'], verify=True))

    decoded = decode_jwt_token(hashed)

    assert decoded is not None

    for k in DEFAULT_OPTIONS:
        assert k in decoded

    assert (decoded["exp"] - valid_time.timestamp()) <= 2

    for k, v in val.items():
        assert decoded["sub"][k] == v


def test_expire_raises_exception():
    """
    Test expiration raises exception
    """

    _, _, val = get_default_data()
    hashed = jwt.encode(
        {
            "exp": (datetime.now() - timedelta(minutes=30, milliseconds=1)).timestamp(),
            "sub": str(val).replace("'", '"'),
            **DEFAULT_OPTIONS,
        },
        st.JWT_SECRET_ENCODE_KEY,
        st.ALGORITHM,
    )

    with pytest.raises(ExpiredSignatureError) as error_context:
        decode_jwt_token(hashed)
        assert error_context is not None
        print(error_context)
