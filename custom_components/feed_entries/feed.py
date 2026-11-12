"""Fetching a feed, and turning it into the list of entries the sensor keeps.

The entries are in the shape the feedparser custom integration writes, so cards made for it read them too: a list of
objects with `id`, `title`, `link` and `published`. The date is ISO 8601 in UTC, which any card can read, unlike a
format of the user's choosing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import struct_time
from typing import Any

import aiohttp
import feedparser
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import TIMEOUT


class FeedError(Exception):
    """The feed couldn't be fetched."""


class NotAFeedError(FeedError):
    """The address answered with something that isn't an RSS or Atom feed."""


@dataclass(frozen=True)
class Feed:
    title: str | None
    link: str | None
    entries: list[dict[str, str]] = field(default_factory=list)


def _time(value: Any) -> datetime | None:
    if isinstance(value, struct_time):
        return datetime(*value[:6], tzinfo=UTC)
    return None


def parse(body: bytes, limit: int) -> Feed:
    """The feed's newest entries, up to `limit`.

    Newest first when every entry has a date, as a feed's own order is usually that but not always. An entry with
    neither a title nor a link is left out. CPU-bound: run it in the executor.
    """
    parsed = feedparser.parse(body)
    if not parsed.get("version"):
        # feedparser parses anything, an HTML page included, and says what it found only through the version.
        raise NotAFeedError(str(parsed.get("bozo_exception") or "no RSS or Atom found"))

    entries: list[tuple[datetime | None, dict[str, str]]] = []
    for item in parsed.entries:
        title = (item.get("title") or "").strip()
        link = (item.get("link") or "").strip()
        if not title and not link:
            continue
        entry = {"id": (item.get("id") or link or title).strip(), "title": title or link}
        if link:
            entry["link"] = link
        time = _time(item.get("published_parsed")) or _time(item.get("updated_parsed"))
        if time:
            entry["published"] = time.isoformat()
        entries.append((time, entry))

    if all(time is not None for time, _ in entries):
        entries.sort(key=lambda pair: pair[0], reverse=True)  # type: ignore[arg-type, return-value]
    channel = parsed.get("feed", {})
    return Feed(
        title=(channel.get("title") or "").strip() or None,
        link=(channel.get("link") or "").strip() or None,
        entries=[entry for _, entry in entries[:limit]],
    )


class FeedClient:
    """Fetches one feed, asking with the ETag and date it last came with, so an unchanged feed costs a 304."""

    def __init__(self, hass: HomeAssistant, url: str) -> None:
        self._hass = hass
        self._url = url
        self._etag: str | None = None
        self._modified: str | None = None
        self._body: bytes | None = None

    async def fetch(self) -> bytes:
        """The feed's body, the last one again when the server says it hasn't changed."""
        headers = {}
        if self._body is not None:
            if self._etag:
                headers["If-None-Match"] = self._etag
            if self._modified:
                headers["If-Modified-Since"] = self._modified
        try:
            async with async_get_clientsession(self._hass).get(
                self._url, headers=headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT.total_seconds())
            ) as response:
                if response.status == 304 and self._body is not None:
                    return self._body
                if response.status != 200:
                    raise FeedError(f"{self._url} answered with status {response.status}")
                body = await response.read()
                self._etag = response.headers.get("ETag")
                self._modified = response.headers.get("Last-Modified")
        except (aiohttp.ClientError, TimeoutError) as err:
            # A timeout's message is empty, and the coordinator logs only the first failure, so the type is the cause.
            raise FeedError(f"{self._url} couldn't be reached: {str(err) or type(err).__name__}") from err
        self._body = body
        return body
