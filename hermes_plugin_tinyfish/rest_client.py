"""TinyFish REST API client used as the API-key fallback path."""

from __future__ import annotations

from typing import Any, cast

import httpx

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"


class TinyFishRestError(RuntimeError):
    """Raised for TinyFish REST transport or HTTP failures."""


def _headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key, "Accept": "application/json"}


def search(query: str, *, api_key: str, timeout: float = 30.0) -> dict[str, Any]:
    """Run a TinyFish Search API query."""

    try:
        response = httpx.get(
            SEARCH_URL,
            params={"query": query},
            headers=_headers(api_key),
            timeout=timeout,
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPStatusError as exc:
        raise TinyFishRestError(f"TinyFish Search returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise TinyFishRestError(f"Could not reach TinyFish Search: {exc}") from exc
    except ValueError as exc:
        raise TinyFishRestError("TinyFish Search returned invalid JSON") from exc


def fetch(
    urls: list[str],
    *,
    api_key: str,
    output_format: str = "markdown",
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Run the TinyFish Fetch API for one or more URLs."""

    try:
        response = httpx.post(
            FETCH_URL,
            json={"urls": urls, "format": output_format},
            headers=_headers(api_key),
            timeout=timeout,
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPStatusError as exc:
        raise TinyFishRestError(f"TinyFish Fetch returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise TinyFishRestError(f"Could not reach TinyFish Fetch: {exc}") from exc
    except ValueError as exc:
        raise TinyFishRestError("TinyFish Fetch returned invalid JSON") from exc
