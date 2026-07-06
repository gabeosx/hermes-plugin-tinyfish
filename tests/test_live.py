from __future__ import annotations

import os

import pytest

from hermes_plugin_tinyfish.provider import TinyFishWebSearchProvider

pytestmark = pytest.mark.skipif(
    os.getenv("TINYFISH_LIVE_TESTS") != "1",
    reason="live TinyFish tests are opt-in",
)


def test_live_search_and_fetch() -> None:
    provider = TinyFishWebSearchProvider()
    search = provider.search("TinyFish web agent", limit=1)
    assert search["success"] is True
    assert search["data"]["web"]

    docs = provider.extract(["https://docs.tinyfish.ai/"], format="markdown")
    assert docs
    assert not docs[0].get("error")
