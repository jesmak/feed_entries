"""Turning a feed into the sensor's entries."""

from __future__ import annotations

import pytest

from custom_components.feed_entries.feed import NotAFeedError, parse

from .conftest import ATOM, HTML, RSS


def test_rss_entries_in_feedparsers_shape_with_iso_dates() -> None:
    feed = parse(RSS, 20)
    assert feed.title == "Example News"
    assert feed.link == "https://news.example.com/"
    assert feed.entries == [
        {
            "id": "1003",
            "title": "Third bulletin",
            "link": "https://news.example.com/3?mtm_campaign=rss&mtm_source=rss",
            "published": "2026-10-21T07:06:08+00:00",
        },
        # +0300 brought to UTC.
        {"id": "1002", "title": "Second bulletin", "link": "https://news.example.com/2", "published": "2026-10-14T18:26:22+00:00"},
        {"id": "1001", "title": "First bulletin", "link": "https://news.example.com/1", "published": "2026-10-13T18:37:18+00:00"},
    ]


def test_entries_are_cut_to_the_limit() -> None:
    assert [entry["id"] for entry in parse(RSS, 2).entries] == ["1003", "1002"]


def test_the_publishing_time_wins_over_the_update_time() -> None:
    body = ATOM.replace(
        b"<published>2026-09-01T10:00:00+02:00</published><updated>2026-09-01T10:00:00+02:00</updated>",
        b"<published>2026-09-01T10:00:00+02:00</published><updated>2026-09-20T10:00:00+02:00</updated>",
    )
    older = next(entry for entry in parse(body, 20).entries if entry["title"] == "Older post")
    assert older["published"] == "2026-09-01T08:00:00+00:00"


def test_an_entry_without_an_id_is_known_by_its_link_and_one_without_either_by_its_title() -> None:
    body = RSS.replace(b'<guid isPermaLink="false">1003</guid>', b"").replace(
        b'<link>https://news.example.com/2</link>\n<guid isPermaLink="false">1002</guid>', b""
    )
    assert [entry["id"] for entry in parse(body, 20).entries] == [
        "https://news.example.com/3?mtm_campaign=rss&mtm_source=rss",
        "Second bulletin",
        "1001",
    ]


def test_the_feeds_own_link_is_kept_only_as_a_web_address() -> None:
    assert parse(RSS.replace(b"<link>https://news.example.com/</link>", b"<link>/</link>"), 20).link is None
    assert parse(RSS.replace(b"<link>https://news.example.com/</link>", b"<link>mailto:news@example.com</link>"), 20).link is None


def test_atom_oldest_first_is_put_newest_first_and_an_update_time_stands_in_for_publishing() -> None:
    feed = parse(ATOM, 1)
    assert feed.title == "Example Blog"
    assert feed.entries == [
        {
            "id": "urn:example:newer",
            "title": "Newer post",
            "link": "https://blog.example.com/newer",
            "published": "2026-10-02T10:00:00+00:00",
        }
    ]


def test_an_entry_without_a_date_keeps_the_feeds_order() -> None:
    body = ATOM.replace(b"<updated>2026-10-02T10:00:00Z</updated></entry>", b"</entry>")
    entries = parse(body, 20).entries
    assert [entry["title"] for entry in entries] == ["Older post", "Newer post"]
    assert "published" not in entries[1]


def test_an_entry_without_a_title_or_a_link_is_left_out_and_one_without_a_title_is_titled_by_its_link() -> None:
    body = RSS.replace(b"<title>Third bulletin</title>", b"").replace(
        b"<item><title>Second bulletin</title><link>https://news.example.com/2</link>", b"<item>"
    )
    entries = parse(body, 20).entries
    assert [entry["title"] for entry in entries] == ["https://news.example.com/3?mtm_campaign=rss&mtm_source=rss", "First bulletin"]


def test_an_html_page_is_not_a_feed() -> None:
    with pytest.raises(NotAFeedError):
        parse(HTML, 20)
