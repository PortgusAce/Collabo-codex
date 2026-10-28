import asyncio

import pytest
from mcp import types

import json
from gateway import Relay, DESKTOP_ALLOWED, HIDDEN_NATIVE, json_result


class FakeClient:
    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments, meta=None):
        self.calls.append((name, arguments, meta))
        if name == "list_projects":
            return json_result({"projects": [
                {"projectId": "local-project", "projectKind": "local", "hostId": "local", "path": "synthetic-folder", "label": "Synthetic"},
                {"projectId": "remote-project", "projectKind": "local", "hostId": "remote", "path": "remote-folder"},
                {"projectId": "cloud-project", "projectKind": "chatgpt", "hostId": None}]})
        return types.CallToolResult(content=[types.TextContent(type="text", text="synthetic result")])


def tool(name):
    return types.Tool(name=name, description="Native description", inputSchema={"type": "object"})


def test_allowlist_annotation_and_source_binding():
    client = FakeClient()
    relay = Relay()
    relay.add(client, [tool(n) for n in DESKTOP_ALLOWED | {"handoff_thread", "automation_update"}],
              desktop=True, anchor="real-setup-thread")
    assert {t.name for t in relay.tools} == DESKTOP_ALLOWED - HIDDEN_NATIVE | {"list_local_projects", "create_work_task"}
    assert not next(t for t in relay.tools if t.name == "create_work_task").annotations.readOnlyHint
    assert next(t for t in relay.tools if t.name == "read_thread").annotations.readOnlyHint
    asyncio.run(relay.call("read_thread", {"threadId": "target"}))
    assert client.calls == [("read_thread", {"threadId": "target"}, {"codexThreadId": "real-setup-thread"})]
    with pytest.raises(ValueError):
        asyncio.run(relay.call("automation_update", {}))
    assert len(client.calls) == 1
    with pytest.raises(ValueError):
        asyncio.run(relay.call_public("create_thread", {"prompt": "must not execute"}))
    assert len(client.calls) == 1


def test_file_calls_do_not_receive_desktop_identity():
    client = FakeClient()
    relay = Relay()
    relay.add(client, [tool("read_file")])
    result = asyncio.run(relay.call("read_file", {"path": "synthetic.txt"}))
    assert not result.isError
    assert client.calls[0][2] is None
    with pytest.raises(ValueError):
        relay.add(client, [tool("read_file")])


def test_project_creation_routes_to_exact_local_project():
    client, relay = FakeClient(), Relay()
    relay.add(client, [tool(n) for n in DESKTOP_ALLOWED], desktop=True, anchor="setup")
    listing = asyncio.run(relay.call_public("list_local_projects", {}))
    assert [p["project_id"] for p in json.loads(listing.content[0].text)["projects"]] == ["local-project"]
    asyncio.run(relay.call_public("create_work_task", {"project_id": "local-project", "prompt": "Write a synthetic document", "title": "Synthetic task"}))
    assert client.calls[-1] == ("create_thread", {"prompt": "Write a synthetic document", "title": "Synthetic task",
        "target": {"type": "project", "projectId": "local-project", "environment": {"type": "local"}}}, {"codexThreadId": "setup"})
    count = sum(name == "create_thread" for name, _, _ in client.calls)
    for invalid in ["cloud-project", "remote-project", "unknown"]:
        with pytest.raises(ValueError):
            asyncio.run(relay.call_public("create_work_task", {"project_id": invalid, "prompt": "reject"}))
    with pytest.raises(ValueError):
        asyncio.run(relay.call_public("create_work_task", {"project_id": "local-project", "prompt": "  "}))
    assert sum(name == "create_thread" for name, _, _ in client.calls) == count
