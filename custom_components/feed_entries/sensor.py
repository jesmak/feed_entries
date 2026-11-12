"""The feed's sensor: the time of its newest entry, with the entries in an attribute."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_ENTRIES, ATTR_FEED_LINK, ATTR_FEED_TITLE, DOMAIN
from .coordinator import FeedConfigEntry, FeedCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: FeedConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([FeedSensor(entry.runtime_data)])


class FeedSensor(CoordinatorEntity[FeedCoordinator], SensorEntity):
    """Its state is when the newest entry was published, so a new entry changes it and can trigger an automation."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:rss"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    # The entries are what the dashboard shows now. Kept out of the recorder, they don't fill its database with a copy at
    # every change, and stay clear of its 16 kB limit on attributes.
    _unrecorded_attributes = frozenset({ATTR_ENTRIES})

    def __init__(self, coordinator: FeedCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=coordinator.data.link if coordinator.data else None,
        )

    @property
    def native_value(self) -> datetime | None:
        published = [entry["published"] for entry in self.coordinator.data.entries if "published" in entry]
        return datetime.fromisoformat(max(published)) if published else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        feed = self.coordinator.data
        return {ATTR_ENTRIES: feed.entries, ATTR_FEED_TITLE: feed.title, ATTR_FEED_LINK: feed.link}
