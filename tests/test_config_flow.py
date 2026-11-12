"""Adding a feed, and its options."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.feed_entries.const import CONF_INTERVAL, CONF_ITEMS, DOMAIN

from .conftest import HTML, RSS, URL


async def start(hass: HomeAssistant, data: dict[str, str]):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], data)


async def test_adds_a_feed_named_by_its_own_title(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(URL, content=RSS)
    result = await start(hass, {CONF_URL: f" {URL} "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Example News"
    assert result["data"] == {CONF_URL: URL}
    assert result["options"] == {CONF_ITEMS: 20, CONF_INTERVAL: 60}
    assert result["result"].unique_id == URL


async def test_a_name_given_replaces_the_feeds_title(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(URL, content=RSS)
    result = await start(hass, {CONF_URL: URL, CONF_NAME: "Bulletins"})
    assert result["title"] == "Bulletins"


async def test_a_page_that_isnt_a_feed_is_refused(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(URL, content=HTML)
    result = await start(hass, {CONF_URL: URL})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_a_feed"}


async def test_an_address_that_doesnt_answer_is_refused(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(URL, status=404)
    result = await start(hass, {CONF_URL: URL})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_a_feed_is_added_once(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=URL, data={CONF_URL: URL}).add_to_hass(hass)
    result = await start(hass, {CONF_URL: URL})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == 0


async def test_options_change_the_entries_kept_and_the_interval(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(URL, content=RSS)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=URL, title="Example News", data={CONF_URL: URL}, options={CONF_ITEMS: 20, CONF_INTERVAL: 60}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_ITEMS: 2, CONF_INTERVAL: 30})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_ITEMS: 2, CONF_INTERVAL: 30}
    # Saving reloaded the entry, which now keeps two.
    state = hass.states.get("sensor.example_news")
    assert state is not None
    assert len(state.attributes["entries"]) == 2
