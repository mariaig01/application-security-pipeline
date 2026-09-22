import secrets
from functools import lru_cache

from werkzeug.security import check_password_hash, generate_password_hash

# OWASP's N=2^15, r=8, p=3 alternative: ~32 MiB per concurrent hash.
HASH_METHOD = "scrypt:32768:8:3"


def hash_password(password):
    return generate_password_hash(password, method=HASH_METHOD)


@lru_cache(maxsize=1)
def dummy_hash():
    return hash_password(secrets.token_urlsafe(32))


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)
