from __future__ import annotations

from hermes_plugin_tinyfish.config import fetch_options, search_options


def test_search_options_cover_live_api_filters() -> None:
    config = {
        "tinyfish": {
            "search": {
                "location": "US",
                "language": "en",
                "include_domains": "github.com,arxiv.org",
                "exclude_domains": "example.com",
                "recency_minutes": "60",
                "after_date": "2026-01-01",
                "before_date": "2026-08-01",
                "domain_type": "research_paper",
                "pub_year_min": "2024",
                "pub_year_max": 2026,
                "page": "2",
                "purpose": "Find primary research",
            }
        }
    }

    assert search_options(config) == {
        "location": "US",
        "language": "en",
        "include_domains": "github.com,arxiv.org",
        "exclude_domains": "example.com",
        "recency_minutes": 60,
        "after_date": "2026-01-01",
        "before_date": "2026-08-01",
        "domain_type": "research_paper",
        "pub_year_min": 2024,
        "pub_year_max": 2026,
        "page": 2,
        "purpose": "Find primary research",
    }


def test_fetch_options_cover_selectors_conditionals_and_intent() -> None:
    config = {
        "tinyfish": {
            "fetch": {
                "ttl": "0",
                "per_url_timeout_ms": 45000,
                "links": "true",
                "image_links": False,
                "purpose": "Read the product table",
                "if_none_match": 'W/"abc"',
                "if_modified_since": "Wed, 21 Oct 2015 07:28:00 GMT",
                "include_etag_and_last_modified": "yes",
                "include_selectors": ["main", " article ", ""],
                "exclude_selectors": ["nav", ".comments"],
            }
        }
    }

    assert fetch_options(config) == {
        "ttl": 0,
        "per_url_timeout_ms": 45000,
        "links": True,
        "image_links": False,
        "purpose": "Read the product table",
        "if_none_match": 'W/"abc"',
        "if_modified_since": "Wed, 21 Oct 2015 07:28:00 GMT",
        "include_etag_and_last_modified": True,
        "include_selectors": ["main", "article"],
        "exclude_selectors": ["nav", ".comments"],
    }


def test_fetch_options_ignore_scalar_selector_values() -> None:
    config = {"tinyfish": {"fetch": {"include_selectors": "article"}}}

    assert fetch_options(config) == {}
