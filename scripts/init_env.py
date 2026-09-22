"""Create a development .env without overwriting an existing configuration."""

import os
import secrets
from pathlib import Path


def main():
    path = Path(__file__).resolve().parents[1] / ".env"
    password = secrets.token_hex(24)
    database_admin_password = secrets.token_hex(24)
    content = (
        "APP_ENV=development\n"
        f"SECRET_KEY={secrets.token_hex(32)}\n"
        "POSTGRES_USER=appsec_bootstrap\nPOSTGRES_DB=appsec\n"
        f"POSTGRES_PASSWORD={database_admin_password}\n"
        f"DB_APP_PASSWORD={password}\n"
        f"DATABASE_URL=postgresql+psycopg://appsec:{password}@db:5432/appsec\n"
        "APP_PORT=8000\nTRUSTED_HOSTS=localhost,127.0.0.1\n"
    )
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit(".env already exists; left unchanged.") from None
    with os.fdopen(fd, "w") as output:
        output.write(content)
    print("Created .env with random secrets and permissions 0600.")


if __name__ == "__main__":
    main()
