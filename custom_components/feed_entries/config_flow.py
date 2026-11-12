"""Config flow: one entry per feed, by its address. Its options are how many entries it keeps and how often it is fetched."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_INTERVAL,
    CONF_ITEMS,
    DEFAULT_INTERVAL,
    DEFAULT_ITEMS,
    DOMAIN,
    MAX_INTERVAL,
    MAX_ITEMS,
    MIN_INTERVAL,
    MIN_ITEMS,
)
from .feed import FeedClient, FeedError, NotAFeedError, parse

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Optional(CONF_NAME): TextSelector(),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ITEMS, default=DEFAULT_ITEMS): NumberSelector(
            NumberSelectorConfig(min=MIN_ITEMS, max=MAX_ITEMS, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): NumberSelector(
            NumberSelectorConfig(min=MIN_INTERVAL, max=MAX_INTERVAL, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="min")
        ),
    }
)


class FeedEntriesConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The feed's address, read once to check that it is a feed, and a name, by default the feed's own title."""
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip()
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()
            try:
                body = await FeedClient(self.hass, url).fetch()
                feed = await self.hass.async_add_executor_job(parse, body, DEFAULT_ITEMS)
            except NotAFeedError as err:
                _LOGGER.debug("%s is not a feed: %s", url, err)
                errors["base"] = "not_a_feed"
            except FeedError as err:
                _LOGGER.debug("%s couldn't be read: %s", url, err)
                errors["base"] = "cannot_connect"
            else:
                title = (user_input.get(CONF_NAME) or "").strip() or feed.title or url
                return self.async_create_entry(
                    title=title,
                    data={CONF_URL: url},
                    options={CONF_ITEMS: DEFAULT_ITEMS, CONF_INTERVAL: DEFAULT_INTERVAL},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FeedEntriesOptionsFlow:
        return FeedEntriesOptionsFlow()


class FeedEntriesOptionsFlow(OptionsFlow):
    """How many entries the feed keeps, and how often it is fetched. Saving reloads the entry."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={CONF_ITEMS: int(user_input[CONF_ITEMS]), CONF_INTERVAL: int(user_input[CONF_INTERVAL])})
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, dict(self.config_entry.options)),
        )
