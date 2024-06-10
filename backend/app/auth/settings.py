""" Variables defined by the environment for JWT"""

import base64
import os


ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", str(30)))
REFRESH_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("JWT_REFRESH_EXPIRE_MINUTES", str(60 * 24 * 2))
)  # 2 dias
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET_KEY = (
    os.environ["JWT_SECRET_KEY"]
    if os.environ.get("ENVIRONMENT", "") == "PROD"
    else base64.b64encode(os.environ["JWT_SECRET_KEY"].encode("ascii")).decode("ascii")
)
JWT_REFRESH_SECRET_KEY = os.environ["JWT_REFRESH_SECRET_KEY"]
