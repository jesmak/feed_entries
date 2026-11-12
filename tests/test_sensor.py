"""The feed's sensor."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_URL, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.feed_entries.const import CONF_INTERVAL, CONF_ITEMS, DOMAIN

from .conftest import RSS, URL


async def setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=URL, title="Example News", data={CONF_URL: URL}, options={CONF_ITEMS: 20, CONF_INTERVAL: 60}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_state_is_the_newest_entrys_time_and_the_entries_are_an_attribute(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, content=RSS)
    await setup(hass)
    state = hass.states.get("sensor.example_news")
    assert state is not None
    assert state.state == "2026-10-21T07:06:08+00:00"
    assert [entry["id"] for entry in state.attributes["entries"]] == ["1003", "1002", "1001"]
    assert state.attributes["feed_title"] == "Example News"
    assert state.attributes["feed_link"] == "https://news.example.com/"


async def test_an_unchanged_feed_is_asked_with_its_etag_and_keeps_its_entries(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    aioclient_mock.get(URL, content=RSS, headers={"ETag": '"v1"'})
    await setup(hass)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=304)

    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][3]["If-None-Match"] == '"v1"'
    state = hass.states.get("sensor.example_news")
    assert state is not None
    assert len(state.attributes["entries"]) == 3


async def test_a_failed_fetch_makes_the_sensor_unavailable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    aioclient_mock.get(URL, content=RSS)
    await setup(hass)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=500)

    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.example_news")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE
