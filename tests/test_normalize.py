from __future__ import annotations

import json

from hermes_plugin_tinyfish.normalize import normalize_fetch_documents, normalize_search_response


def test_normalize_search_rest_shape() -> None:
    payload = {
        "query": "tinyfish",
        "results": [
            {
                "position": 1,
                "title": "TinyFish",
                "snippet": "Search and fetch",
                "url": "https://www.tinyfish.ai/",
            }
        ],
    }

    assert normalize_search_response(payload, limit=5) == {
        "success": True,
        "data": {
            "web": [
                {
                    "title": "TinyFish",
                    "url": "https://www.tinyfish.ai/",
                    "description": "Search and fetch",
                    "position": 1,
                }
            ]
        },
    }


def test_normalize_search_mcp_wrapper() -> None:
    wrapped = json.dumps(
        {
            "result": json.dumps(
                {
                    "results": [
                        {
                            "title": "Docs",
                            "url": "https://docs.tinyfish.ai/",
                            "snippet": "Documentation",
                        }
                    ]
                }
            )
        }
    )

    result = normalize_search_response(wrapped, limit=1)
    assert result["data"]["web"][0]["title"] == "Docs"


def test_normalize_fetch_rest_shape() -> None:
    payload = {
        "results": [
            {
                "url": "https://docs.tinyfish.ai/",
                "final_url": "https://docs.tinyfish.ai/",
                "title": "TinyFish Docs",
                "text": "# TinyFish",
                "format": "markdown",
            }
        ],
        "errors": [],
    }

    docs = normalize_fetch_documents(payload, fallback_urls=["https://docs.tinyfish.ai/"])
    assert docs[0]["title"] == "TinyFish Docs"
    assert docs[0]["content"] == "# TinyFish"
    assert docs[0]["metadata"]["sourceURL"] == "https://docs.tinyfish.ai/"


def test_normalize_search_preserves_news_and_research_metadata() -> None:
    payload = {
        "results": [
            {
                "position": 1,
                "site_name": "Journal",
                "title": "Paper",
                "snippet": "Abstract",
                "url": "https://example.com/paper",
                "date": "2026-08-01",
                "publisher": "Publisher",
                "authors": ["A. Author"],
                "venue": "Conference",
                "year": 2026,
                "cited_by_count": 42,
            }
        ]
    }

    result = normalize_search_response(payload)["data"]["web"][0]

    assert result["site_name"] == "Journal"
    assert result["date"] == "2026-08-01"
    assert result["publisher"] == "Publisher"
    assert result["authors"] == ["A. Author"]
    assert result["venue"] == "Conference"
    assert result["year"] == 2026
    assert result["cited_by_count"] == 42


def test_normalize_fetch_json_tree_and_new_metadata() -> None:
    tree = {"type": "document", "children": [{"type": "heading", "text": "Title"}]}
    payload = {
        "results": [
            {
                "url": "https://example.com",
                "text": tree,
                "author": "Ada",
                "published_date": "2026-08-29",
                "links": ["https://example.com/about"],
                "image_links": ["https://example.com/image.png"],
                "not_modified": True,
                "etag": 'W/"abc"',
                "last_modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                "unmatched_selectors": [".missing"],
                "latency_ms": 123.4,
                "format": "json",
            }
        ],
        "errors": [],
    }

    doc = normalize_fetch_documents(payload, fallback_urls=["https://example.com"])[0]

    assert doc["content"] == json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    assert doc["metadata"] == {
        "sourceURL": "https://example.com",
        "finalURL": "https://example.com",
        "description": "",
        "language": "",
        "author": "Ada",
        "publishedDate": "2026-08-29",
        "links": ["https://example.com/about"],
        "imageLinks": ["https://example.com/image.png"],
        "notModified": True,
        "etag": 'W/"abc"',
        "lastModified": "Wed, 21 Oct 2015 07:28:00 GMT",
        "unmatchedSelectors": [".missing"],
        "latencyMs": 123.4,
        "format": "json",
    }


def test_normalize_fetch_preserves_input_order_across_successes_and_errors() -> None:
    payload = {
        "results": [{"url": "https://b.example", "text": "b"}],
        "errors": [
            {
                "url": "https://a.example",
                "error": "selector_not_matched",
                "unmatched_selectors": ["article"],
                "candidate_selectors": ["main", "#content"],
            }
        ],
    }

    docs = normalize_fetch_documents(payload, fallback_urls=["https://a.example", "https://b.example"])

    assert [doc["url"] for doc in docs] == ["https://a.example", "https://b.example"]
    assert docs[0]["error"] == "selector_not_matched"
    assert docs[0]["metadata"]["unmatchedSelectors"] == ["article"]
    assert docs[0]["metadata"]["candidateSelectors"] == ["main", "#content"]
    assert docs[1]["content"] == "b"
