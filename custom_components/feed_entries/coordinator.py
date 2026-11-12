"""Fetching one feed on the interval its options set."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_INTERVAL, CONF_ITEMS, DEFAULT_INTERVAL, DEFAULT_ITEMS, DOMAIN
from .feed import Feed, FeedClient, FeedError, parse

_LOGGER = logging.getLogger(__name__)

type FeedConfigEntry = ConfigEntry[FeedCoordinator]


class FeedCoordinator(DataUpdateCoordinator[Feed]):
    config_entry: FeedConfigEntry

    def __init__(self, hass: HomeAssistant, entry: FeedConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(minutes=int(entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL))),
        )
        self.items = int(entry.options.get(CONF_ITEMS, DEFAULT_ITEMS))
        self._client = FeedClient(hass, entry.data[CONF_URL])

    async def _async_update_data(self) -> Feed:
        try:
            body = await self._client.fetch()
            return await self.hass.async_add_executor_job(parse, body, self.items)
        except FeedError as err:
            raise UpdateFailed(str(err)) from err
