import tkinter as tk

from discord_logger import config
from discord_logger.async_runner import AsyncRunner
from discord_logger.client import DiscordClient
from ui.log_view import LogWindow
from ui.picker import PickerWindow
from ui.token_dialog import TokenDialog


def _validate(runner: AsyncRunner, token: str):
    client = DiscordClient(token)
    try:
        user = runner.run(client.get_current_user())
    except Exception:
        return client, None
    return client, user


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    runner = AsyncRunner()
    try:
        while True:
            token = config.load_token()
            client, user = (None, None)
            if token:
                client, user = _validate(runner, token)
            if user is None:
                error = (
                    "The saved token was rejected by Discord. Please enter a new one."
                    if token
                    else None
                )
                token = TokenDialog(root, error=error).show()
                if not token:
                    break
                config.save_token(token)
                client, user = _validate(runner, token)
                if user is None:
                    continue

            choice = PickerWindow(root, runner, client, user).show()
            if choice is None:
                break
            if choice.get("action") == "logout":
                config.clear_token()
                continue

            if not LogWindow(root, runner, client, choice).show():
                break
    finally:
        runner.close()
        root.destroy()


if __name__ == "__main__":
    main()
