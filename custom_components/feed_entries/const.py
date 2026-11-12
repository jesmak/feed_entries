"""Constants for the Feed entries integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "feed_entries"

CONF_ITEMS: Final = "items"
CONF_INTERVAL: Final = "interval"

DEFAULT_ITEMS: Final = 20
MIN_ITEMS: Final = 1
MAX_ITEMS: Final = 200

# In minutes. An hour is what core's feedreader and the feedparser integration use.
DEFAULT_INTERVAL: Final = 60
MIN_INTERVAL: Final = 5
MAX_INTERVAL: Final = 1440

TIMEOUT: Final = timedelta(seconds=30)

ATTR_ENTRIES: Final = "entries"
ATTR_FEED_TITLE: Final = "feed_title"
ATTR_FEED_LINK: Final = "feed_link"
