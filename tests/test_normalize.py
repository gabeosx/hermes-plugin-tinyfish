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
