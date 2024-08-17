from os import environ
import re


BROKER_HOST=str(re.sub(r'\n', '', environ.get("BROKER_HOST", "my-rabbit")))
BROKER_USER=str(re.sub(r'\n', '', environ.get("BROKER_USER", "guest")))
BROKER_PORT=int(re.sub(r'\n', '', environ.get("BROKER_PORT", "5672")))
BROKER_PASS=str(re.sub(r'\n', '', environ.get("BROKER_PASS", "guest")))
