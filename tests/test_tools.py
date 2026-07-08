from __future__ import annotations

import json

from hermes_plugin_tinyfish.tools import handle_agent_run


def test_agent_tool_blocks_without_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    payload = json.loads(handle_agent_run({"url": "https://example.com", "goal": "read"}))

    assert payload["success"] is False
    assert "policy is 'deny'" in payload["error"]
