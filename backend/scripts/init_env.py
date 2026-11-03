"""Create backend/.env from .env.example and fill in a random JWT secret.

    python -m scripts.init_env

Safe to run again: an existing .env is never overwritten.
"""

import secrets
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
EMPTY_SECRET_LINE = "JWT_SECRET_KEY="


def main() -> None:
    env_path = BACKEND_DIR / ".env"
    if env_path.exists():
        print(".env already exists - left unchanged.")
        return

    lines = (BACKEND_DIR / ".env.example").read_text(encoding="utf-8").splitlines()
    if EMPTY_SECRET_LINE not in lines:
        raise SystemExit(f"Could not find the line '{EMPTY_SECRET_LINE}' in .env.example.")

    lines[lines.index(EMPTY_SECRET_LINE)] = EMPTY_SECRET_LINE + secrets.token_urlsafe(48)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Created .env with a new random JWT secret.")


if __name__ == "__main__":
    main()
