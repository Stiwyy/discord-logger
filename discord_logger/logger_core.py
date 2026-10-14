import asyncio
import os
from datetime import datetime
from typing import Callable, Dict, Optional, Set

from .client import DiscordClient
from .config import BASE_URL, LOG_DIR
from .utils import clean_name

POLL_INTERVAL = 0.5


class MessageLogger:
    def __init__(
        self,
        client: DiscordClient,
        target: Dict,
        on_message: Optional[Callable[[Dict], None]] = None,
        on_deleted: Optional[Callable[[Dict], None]] = None,
        on_status: Optional[Callable[[int], None]] = None,
    ):
        self.client = client
        self.target = target
        self.on_message = on_message
        self.on_deleted = on_deleted
        self.on_status = on_status

        self.logged_messages: Dict[str, str] = {}
        self.previous_window_ids: Set[str] = set()
        self.deleted_ids: Set[str] = set()
        self.total = 0
        self.active = True

    @property
    def log_path(self) -> str:
        server_dir = clean_name(self.target.get("server") or "DMs")
        channel_dir = clean_name(self.target.get("channel") or "unknown")
        return os.path.join(LOG_DIR, server_dir, f"live_{channel_dir}.txt")

    async def run(self) -> int:
        path = self.log_path
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if os.path.exists(path) and os.path.getsize(path) > 0:
            sep = datetime.now().strftime("--- %Y-%m-%d %H:%M:%S ---\n")
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n" + sep)

        with open(path, "a", encoding="utf-8") as log_file:
            while self.active:
                await self._poll(log_file)
                await asyncio.sleep(POLL_INTERVAL)
        return self.total

    async def _poll(self, log_file) -> None:
        url = f"{BASE_URL}/channels/{self.target['channel_id']}/messages?limit=50"
        msgs = await self.client.get_json(url) or []
        current_ids = {m["id"] for m in msgs}

        self._detect_deletions(log_file, current_ids)
        self.previous_window_ids = current_ids

        for m in reversed(msgs):
            if m["id"] not in self.logged_messages:
                entry, display = await self._build_entry(m)
                log_file.write(entry)
                log_file.flush()
                self.logged_messages[m["id"]] = entry
                self.total += 1
                if self.on_message:
                    self.on_message(display)

        if self.on_status:
            self.on_status(self.total)

    def _detect_deletions(self, log_file, current_ids: Set[str]) -> None:
        for mid in self.previous_window_ids:
            if mid in current_ids or mid in self.deleted_ids:
                continue
            entry = self.logged_messages.get(mid, "").rstrip("\n")
            if entry:
                self._flag_deleted_in_file(entry)
            self.deleted_ids.add(mid)
            if self.on_deleted:
                self.on_deleted({"id": mid, "entry": entry})

    def _flag_deleted_in_file(self, entry: str) -> None:
        path = self.log_path
        with open(path, "r+", encoding="utf-8") as f:
            data = f.read()
            f.seek(0)
            f.write(data.replace(entry, f"{entry} [DELETED]", 1))
            f.truncate()

    async def _build_entry(self, m: Dict):
        ts = m["timestamp"]
        date, _, rest = ts.partition("T")
        time = rest.split(".")[0]
        author = m["author"]["username"]
        content = m["content"] or ""

        entry = f"[ID: {m['id']}] On {date} at {time}, {author} said: {content}\n"
        replies = []

        ref_id = (m.get("message_reference") or {}).get("message_id")
        if ref_id:
            orig = await self.client.get_message(self.target["channel_id"], ref_id)
            if orig:
                entry += (
                    f"Forwarded from {orig['author']['username']} said: "
                    f"{orig['content']}\n"
                )
                replies.append(
                    {
                        "author": orig["author"]["username"],
                        "content": orig["content"],
                        "deleted": False,
                    }
                )
            else:
                entry += f"Forwarded from msg ID: {ref_id} [DELETED]\n"
                replies.append({"ref_id": ref_id, "deleted": True})

        display = {
            "id": m["id"],
            "date": date,
            "time": time,
            "author": author,
            "content": content,
            "replies": replies,
        }
        return entry, display

    def stop(self) -> None:
        self.active = False
