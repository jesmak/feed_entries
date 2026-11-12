"""Shared fixtures: made-up feeds shaped like real ones."""

from __future__ import annotations

import pytest

URL = "https://news.example.com/feed.xml"

# RSS 2.0 as a news site writes it: guids that aren't links, links with campaign tags, RFC 822 dates in a mix of zones,
# entries newest first.
RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Example News</title><link>https://news.example.com/</link><description>Made up</description>
<item><title>Third bulletin</title><link>https://news.example.com/3?mtm_campaign=rss&amp;mtm_source=rss</link>
<guid isPermaLink="false">1003</guid><pubDate>Wed, 21 Oct 2026 07:06:08 GMT</pubDate></item>
<item><title>Second bulletin</title><link>https://news.example.com/2</link>
<guid isPermaLink="false">1002</guid><pubDate>Wed, 14 Oct 2026 21:26:22 +0300</pubDate></item>
<item><title>First bulletin</title><link>https://news.example.com/1</link>
<guid isPermaLink="false">1001</guid><pubDate>Tue, 13 Oct 2026 18:37:18 GMT</pubDate></item>
</channel></rss>
"""

# Atom, oldest first, one entry with only an update time and one with no date at all.
ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Example Blog</title><link href="https://blog.example.com/"/><id>urn:example:blog</id><updated>2026-10-02T10:00:00Z</updated>
<entry><title>Older post</title><link href="https://blog.example.com/older"/><id>urn:example:older</id>
<published>2026-09-01T10:00:00+02:00</published><updated>2026-09-01T10:00:00+02:00</updated></entry>
<entry><title>Newer post</title><link href="https://blog.example.com/newer"/><id>urn:example:newer</id>
<updated>2026-10-02T10:00:00Z</updated></entry>
</feed>
"""

HTML = b"<!doctype html><html><head><title>Example</title></head><body><p>Not a feed</p></body></html>"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    return None
