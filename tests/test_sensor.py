"""The feed's sensor."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
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
    entry = await setup(hass)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=500)

    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.example_news")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    # Back as soon as a fetch succeeds. Refreshed directly, as a second tick of the frozen clock after a failure doesn't
    # always reach the coordinator's own schedule.
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, content=RSS)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get("sensor.example_news")
    assert state is not None
    assert state.state == "2026-10-21T07:06:08+00:00"


async def test_a_not_modified_before_any_feed_is_a_failure_and_setup_is_retried(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, status=304)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=URL, title="Example News", data={CONF_URL: URL}, options={CONF_ITEMS: 20, CONF_INTERVAL: 60}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_the_date_a_feed_came_with_is_sent_back(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    aioclient_mock.get(URL, content=RSS, headers={"Last-Modified": "Wed, 21 Oct 2026 07:06:08 GMT"})
    await setup(hass)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=304)

    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert aioclient_mock.mock_calls[0][3]["If-Modified-Since"] == "Wed, 21 Oct 2026 07:06:08 GMT"
    assert "If-None-Match" not in aioclient_mock.mock_calls[0][3]


async def test_a_feed_whose_own_link_isnt_a_web_address_still_gets_its_sensor(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, content=RSS.replace(b"<link>https://news.example.com/</link>", b"<link>/</link>"))
    await setup(hass)
    state = hass.states.get("sensor.example_news")
    assert state is not None
    assert state.attributes["feed_link"] is None
