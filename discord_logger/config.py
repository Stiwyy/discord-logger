import os
from typing import Optional

BASE_URL = "https://discord.com/api/v10"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

LOG_DIR = "logs"


def load_token() -> Optional[str]:
    if not os.path.exists(ENV_FILE):
        return None
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("DISCORD_TOKEN="):
                token = line.strip().split("=", 1)[1].strip()
                return token or None
    return None


def _save_value(key: str, value: str) -> None:
    values = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                name, sep, current = line.rstrip("\n").partition("=")
                if sep:
                    values[name] = current
    values[key] = value
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        for name, current in values.items():
            f.write(f"{name}={current}\n")
    try:
        os.chmod(ENV_FILE, 0o600)
    except OSError:
        pass


def save_token(token: str) -> None:
    """Persist the token locally."""
    _save_value("DISCORD_TOKEN", token)


def load_webhook() -> Optional[str]:
    if not os.path.exists(ENV_FILE):
        return None
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("DISCORD_WEBHOOK="):
                return line.strip().split("=", 1)[1].strip() or None
    return None


def save_webhook(url: str) -> None:
    _save_value("DISCORD_WEBHOOK", url)


def clear_token() -> None:
    """Remove the saved token, if any."""
    if os.path.exists(ENV_FILE):
        os.remove(ENV_FILE)
