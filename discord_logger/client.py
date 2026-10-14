from typing import Dict, List, Optional

import aiohttp

from .config import BASE_URL


class DiscordAPIError(Exception):
    def __init__(self, status, url: str):
        self.status = status
        super().__init__(f"Discord API returned {status} for {url}")


class DiscordAuthError(DiscordAPIError):
    pass


class DiscordClient:
    def __init__(self, token: str):
        self._token = token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": self._token,
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def get_json(self, url: str):
        session = await self._ensure_session()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status in (401, 403):
                    raise DiscordAuthError(resp.status, url)
                raise DiscordAPIError(resp.status, url)
        except aiohttp.ClientError as exc:
            raise DiscordAPIError(getattr(exc, "status", "n/a"), url) from exc

    async def get_bytes(self, url: str) -> bytes:
        session = await self._ensure_session()
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def get_current_user(self) -> Dict:
        return await self.get_json(f"{BASE_URL}/users/@me")

    async def get_user_guilds(self) -> List[Dict]:
        return await self.get_json(f"{BASE_URL}/users/@me/guilds") or []

    async def get_guild_channels(self, guild_id: str) -> List[Dict]:
        data = await self.get_json(f"{BASE_URL}/guilds/{guild_id}/channels") or []
        return [ch for ch in data if ch.get("type") == 0]

    async def get_dm_channels(self) -> List[Dict]:
        data = await self.get_json(f"{BASE_URL}/users/@me/channels") or []
        return [ch for ch in data if ch.get("type") in (1, 3)]

    async def get_message(self, channel_id: str, message_id: str) -> Optional[Dict]:
        try:
            return await self.get_json(
                f"{BASE_URL}/channels/{channel_id}/messages/{message_id}"
            )
        except DiscordAPIError:
            return None
