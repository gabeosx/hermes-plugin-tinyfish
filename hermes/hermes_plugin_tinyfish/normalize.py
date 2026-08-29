"""Normalize TinyFish MCP and REST payloads into Hermes web-provider shapes."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Any, cast


class TinyFishPayloadError(ValueError):
    """Raised when a TinyFish or MCP payload reports an error."""


def parse_jsonish(value: Any) -> Any:
    """Parse JSON strings when possible and return other values unchanged."""

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return value
    return value


def unwrap_mcp_payload(raw: Any) -> Any:
    """Convert Hermes' MCP wrapper output to the underlying TinyFish payload."""

    payload = parse_jsonish(raw)
    if isinstance(payload, dict) and payload.get("error"):
        raise TinyFishPayloadError(str(payload["error"]))

    if isinstance(payload, dict) and "structuredContent" in payload:
        structured = payload.get("structuredContent")
        if structured is not None:
            return structured

    if isinstance(payload, dict) and "result" in payload:
        result = parse_jsonish(payload.get("result"))
        if isinstance(result, dict) and result.get("error"):
            raise TinyFishPayloadError(str(result["error"]))
        return result

    return payload


def _document_text(value: Any) -> str:
    """Serialize TinyFish's JSON document tree without Python repr leakage."""

    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _copy_present(source: dict[str, Any], target: dict[str, Any], fields: dict[str, str]) -> None:
    for source_key, target_key in fields.items():
        if source_key in source and source[source_key] is not None:
            target[target_key] = source[source_key]


def normalize_search_response(payload: Any, limit: int = 5) -> dict[str, Any]:
    """Return Hermes' standard web-search response envelope."""

    data = unwrap_mcp_payload(payload)
    if isinstance(data, list):
        results = data
    elif isinstance(data, dict):
        if data.get("error"):
            raise TinyFishPayloadError(str(data["error"]))
        if isinstance(data.get("data"), dict) and isinstance(data["data"].get("web"), list):
            return {
                "success": True,
                "data": {"web": data["data"]["web"][: max(1, int(limit or 5))]},
            }
        results = data.get("results") or data.get("web") or []
    else:
        results = []

    count = max(1, int(limit or 5))
    web_results: list[dict[str, Any]] = []
    for idx, item in enumerate(list(results)[:count]):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("link") or "")
        normalized = {
            "title": str(item.get("title") or item.get("site_name") or url),
            "url": url,
            "description": str(
                item.get("snippet")
                or item.get("description")
                or item.get("content")
                or item.get("text")
                or ""
            ),
            "position": int(item.get("position") or idx + 1),
        }
        _copy_present(
            item,
            normalized,
            {
                "site_name": "site_name",
                "date": "date",
                "publisher": "publisher",
                "authors": "authors",
                "venue": "venue",
                "year": "year",
                "cited_by_count": "cited_by_count",
            },
        )
        web_results.append(normalized)
    return {"success": True, "data": {"web": web_results}}


def normalize_fetch_documents(payload: Any, fallback_urls: list[str] | None = None) -> list[dict[str, Any]]:
    """Return Hermes' standard extract document list."""

    urls = list(fallback_urls or [])
    data = unwrap_mcp_payload(payload)
    if isinstance(data, dict) and data.get("error"):
        raise TinyFishPayloadError(str(data["error"]))

    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return cast(list[dict[str, Any]], data["data"])

    if isinstance(data, dict):
        results = data.get("results") or data.get("documents") or []
        errors = data.get("errors") or data.get("failed_results") or []
    elif isinstance(data, list):
        results = data
        errors = []
    else:
        results = []
        errors = []

    documents: list[dict[str, Any]] = []
    for idx, item in enumerate(list(results)):
        if isinstance(item, str):
            url = urls[idx] if idx < len(urls) else ""
            documents.append(
                {
                    "url": url,
                    "title": "",
                    "content": item,
                    "raw_content": item,
                    "metadata": {"sourceURL": url},
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("final_url") or (urls[idx] if idx < len(urls) else ""))
        raw = _document_text(
            item.get("text")
            if item.get("text") is not None
            else item.get("markdown")
            if item.get("markdown") is not None
            else item.get("raw_content")
            if item.get("raw_content") is not None
            else item.get("content")
        )
        metadata: dict[str, Any] = {
            "sourceURL": url,
            "finalURL": str(item.get("final_url") or url),
            "description": str(item.get("description") or ""),
            "language": str(item.get("language") or ""),
        }
        _copy_present(
            item,
            metadata,
            {
                "author": "author",
                "published_date": "publishedDate",
                "links": "links",
                "image_links": "imageLinks",
                "not_modified": "notModified",
                "etag": "etag",
                "last_modified": "lastModified",
                "unmatched_selectors": "unmatchedSelectors",
                "latency_ms": "latencyMs",
                "format": "format",
            },
        )
        documents.append(
            {
                "url": url,
                "title": str(item.get("title") or ""),
                "content": raw,
                "raw_content": raw,
                "metadata": metadata,
            }
        )

    for idx, item in enumerate(list(errors)):
        if isinstance(item, dict):
            url = str(item.get("url") or (urls[idx] if idx < len(urls) else ""))
            error = str(item.get("error") or item.get("message") or "fetch failed")
        else:
            url = urls[idx] if idx < len(urls) else ""
            error = str(item)
        metadata = {"sourceURL": url}
        if isinstance(item, dict):
            _copy_present(
                item,
                metadata,
                {
                    "status": "status",
                    "unmatched_selectors": "unmatchedSelectors",
                    "candidate_selectors": "candidateSelectors",
                },
            )
        documents.append(
            {
                "url": url,
                "title": "",
                "content": "",
                "raw_content": "",
                "error": error,
                "metadata": metadata,
            }
        )

    if not urls:
        return documents

    # TinyFish separates successes and failures into different arrays. Restore
    # the caller's URL order because Hermes associates provider results by
    # position when it merges cache hits and fresh fetches.
    by_url: defaultdict[str, deque[dict[str, Any]]] = defaultdict(deque)
    unaddressed: deque[dict[str, Any]] = deque()
    for document in documents:
        document_url = str(document.get("url") or "")
        if document_url:
            by_url[document_url].append(document)
        else:
            unaddressed.append(document)

    ordered: list[dict[str, Any]] = []
    consumed: set[int] = set()
    for url in urls:
        if by_url[url]:
            document = by_url[url].popleft()
        elif unaddressed:
            document = unaddressed.popleft()
            document["url"] = url
            metadata = document.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata["sourceURL"] = url
        else:
            document = {
                "url": url,
                "title": "",
                "content": "",
                "raw_content": "",
                "error": "TinyFish returned no content",
                "metadata": {"sourceURL": url},
            }
        consumed.add(id(document))
        ordered.append(document)

    ordered.extend(document for document in documents if id(document) not in consumed)
    return ordered
