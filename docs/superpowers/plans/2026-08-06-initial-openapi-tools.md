# Initial HiAgent OpenAPI Tools Implementation Plan

> 状态：历史计划（未采用为当前实现），仅留档。当前实现见 `server/mcp_server_hiagent/compatibility/hiagent-v3.1`（modular 结构），工具集已演进为知识引擎工具。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three explicit read-only MCP tools backed by HiAgent Platform OpenAPI and verify them against the private deployment through an SSH tunnel.

**Architecture:** A focused `tools.py` module translates typed MCP inputs into exact OpenAPI request bodies. `HiAgentOpenAPIClient` remains the only signing and HTTP boundary, while `server.py` constructs one client and registers thin FastMCP wrappers. Tests inject a recording client so credentials and network access are never needed for unit coverage.

**Tech Stack:** Python 3.11, FastMCP 3.x, standard-library `datetime`, `pytest`, HiAgent AK/SK V4 signing.

---

## File Map

- Create `server/mcp_server_hiagent/src/mcp_server_hiagent/tools.py`: typed handlers and pagination validation.
- Create `server/mcp_server_hiagent/tests/test_tools.py`: request mapping and validation tests.
- Create `server/mcp_server_hiagent/tests/test_server.py`: FastMCP registration tests.
- Modify `server/mcp_server_hiagent/src/mcp_server_hiagent/server.py`: client construction, injection, and tool registration.
- Modify `server/mcp_server_hiagent/README.md`: initial tool catalog and private-network test instructions.

### Task 1: Add Typed OpenAPI Tool Handlers

**Files:**
- Create: `server/mcp_server_hiagent/tests/test_tools.py`
- Create: `server/mcp_server_hiagent/src/mcp_server_hiagent/tools.py`

- [ ] **Step 1: Write failing request-mapping tests**

Create a recording client with the same `call` boundary as
`HiAgentOpenAPIClient`, then cover all three actions:

```python
from __future__ import annotations

from typing import Any

import pytest

from mcp_server_hiagent.tools import get_workflow, list_apps, list_workflows


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call(self, **kwargs: Any) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"ResponseMetadata": {"Action": kwargs["action"]}, "Result": {}}


def test_list_apps_builds_required_filter() -> None:
    client = RecordingClient()

    result = list_apps(
        client,
        page_number=2,
        page_size=10,
        app_name="demo",
        workspace_ids=["workspace-1"],
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-08-06T00:00:00Z",
    )

    assert result["ResponseMetadata"] == {"Action": "ListApp"}
    assert client.calls == [
        {
            "action": "ListApp",
            "version": "2023-08-01",
            "service": "app",
            "body": {
                "ListOpt": {"PageNumber": 2, "PageSize": 10},
                "Filter": {
                    "StartTime": "2026-01-01T00:00:00Z",
                    "EndTime": "2026-08-06T00:00:00Z",
                    "AppName": "demo",
                    "WorkspaceIDs": ["workspace-1"],
                },
            },
        }
    ]


def test_list_workflows_builds_workspace_request() -> None:
    client = RecordingClient()

    list_workflows(
        client,
        workspace_id="workspace-1",
        page_number=1,
        page_size=20,
        name_search="flow",
    )

    assert client.calls[0] == {
        "action": "ListWorkflows",
        "version": "2023-08-01",
        "service": "app",
        "body": {
            "WorkspaceID": "workspace-1",
            "ListOpt": {"PageNumber": 1, "PageSize": 20},
            "Filter": {"NameSearch": "flow"},
        },
    }


def test_get_workflow_builds_identity_request() -> None:
    client = RecordingClient()

    get_workflow(
        client,
        workspace_id="workspace-1",
        workflow_id="workflow-1",
    )

    assert client.calls[0] == {
        "action": "GetWorkflow",
        "version": "2023-08-01",
        "service": "app",
        "body": {"WorkspaceID": "workspace-1", "ID": "workflow-1"},
    }


@pytest.mark.parametrize(
    ("page_number", "page_size"),
    [(0, 20), (1, 0), (1, 101)],
)
def test_list_apps_rejects_invalid_pagination(
    page_number: int,
    page_size: int,
) -> None:
    with pytest.raises(ValueError):
        list_apps(
            RecordingClient(),
            page_number=page_number,
            page_size=page_size,
            end_time="2026-08-06T00:00:00Z",
        )
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
cd server/mcp_server_hiagent
uv run pytest tests/test_tools.py -q
```

Expected: collection fails with
`ModuleNotFoundError: No module named 'mcp_server_hiagent.tools'`.

- [ ] **Step 3: Implement the minimal handlers**

Create `src/mcp_server_hiagent/tools.py`:

```python
"""Typed MCP handlers backed by HiAgent Platform OpenAPI."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from typing import Protocol


OPENAPI_VERSION = "2023-08-01"
OPENAPI_SERVICE = "app"
DEFAULT_START_TIME = "1970-01-01T00:00:00Z"


class OpenAPIClient(Protocol):
    def call(
        self,
        *,
        action: str,
        body: Mapping[str, object] | None = None,
        version: str = OPENAPI_VERSION,
        service: str | None = None,
        timeout_seconds: float = 30,
    ) -> dict[str, object]: ...


def _validate_pagination(page_number: int, page_size: int) -> None:
    if page_number < 1:
        raise ValueError("page_number must be at least 1")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")


def _current_utc_time() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def list_apps(
    client: OpenAPIClient,
    *,
    page_number: int = 1,
    page_size: int = 20,
    app_name: str | None = None,
    workspace_ids: Sequence[str] | None = None,
    start_time: str = DEFAULT_START_TIME,
    end_time: str | None = None,
) -> dict[str, object]:
    _validate_pagination(page_number, page_size)
    app_filter: dict[str, object] = {
        "StartTime": start_time,
        "EndTime": end_time or _current_utc_time(),
    }
    if app_name:
        app_filter["AppName"] = app_name
    if workspace_ids:
        app_filter["WorkspaceIDs"] = list(workspace_ids)
    return client.call(
        action="ListApp",
        version=OPENAPI_VERSION,
        service=OPENAPI_SERVICE,
        body={
            "ListOpt": {"PageNumber": page_number, "PageSize": page_size},
            "Filter": app_filter,
        },
    )


def list_workflows(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    page_number: int = 1,
    page_size: int = 20,
    name_search: str | None = None,
) -> dict[str, object]:
    _validate_pagination(page_number, page_size)
    body: dict[str, object] = {
        "WorkspaceID": workspace_id,
        "ListOpt": {"PageNumber": page_number, "PageSize": page_size},
    }
    if name_search is not None:
        body["Filter"] = {"NameSearch": name_search}
    return client.call(
        action="ListWorkflows",
        version=OPENAPI_VERSION,
        service=OPENAPI_SERVICE,
        body=body,
    )


def get_workflow(
    client: OpenAPIClient,
    *,
    workspace_id: str,
    workflow_id: str,
) -> dict[str, object]:
    return client.call(
        action="GetWorkflow",
        version=OPENAPI_VERSION,
        service=OPENAPI_SERVICE,
        body={"WorkspaceID": workspace_id, "ID": workflow_id},
    )
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```bash
cd server/mcp_server_hiagent
uv run pytest tests/test_tools.py -q
```

Expected: `6 passed`.

- [ ] **Step 5: Commit the handler slice**

```bash
git add server/mcp_server_hiagent/src/mcp_server_hiagent/tools.py \
  server/mcp_server_hiagent/tests/test_tools.py
git commit -m "feat: add read-only OpenAPI handlers [Meego-7358746283]"
```

### Task 2: Register FastMCP Tools

**Files:**
- Create: `server/mcp_server_hiagent/tests/test_server.py`
- Modify: `server/mcp_server_hiagent/src/mcp_server_hiagent/server.py`

- [ ] **Step 1: Write the failing registration test**

```python
from __future__ import annotations

import asyncio
from typing import Any

from mcp_server_hiagent.server import create_mcp_server


class RecordingClient:
    def call(self, **kwargs: Any) -> dict[str, object]:
        return {"ResponseMetadata": {"Action": kwargs["action"]}, "Result": {}}


def test_server_registers_initial_openapi_tools() -> None:
    server = create_mcp_server(client=RecordingClient())

    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert names == {
        "health_check",
        "list_apps",
        "list_workflows",
        "get_workflow",
    }
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
cd server/mcp_server_hiagent
uv run pytest tests/test_server.py -q
```

Expected: FAIL because `create_mcp_server` does not accept `client`.

- [ ] **Step 3: Add client injection and thin FastMCP wrappers**

Update `server.py` to:

```python
"""FastMCP server definition for HiAgent."""

from __future__ import annotations

from fastmcp import FastMCP

from mcp_server_hiagent.client import HiAgentOpenAPIClient
from mcp_server_hiagent.config import load_hiagent_config
from mcp_server_hiagent.tools import (
    OpenAPIClient,
    get_workflow as get_workflow_handler,
    list_apps as list_apps_handler,
    list_workflows as list_workflows_handler,
)


def create_mcp_server(client: OpenAPIClient | None = None) -> FastMCP:
    hiagent_config = load_hiagent_config()
    openapi_client = client or HiAgentOpenAPIClient(hiagent_config)
    mcp = FastMCP(
        name="hiagent-mcp-server",
        instructions=(
            "HiAgent MCP Server exposes selected HiAgent OpenAPI capabilities. "
            "This server supports streamable-http transport only and AK/SK "
            "authentication only."
        ),
    )

    @mcp.tool()
    def health_check() -> dict[str, object]:
        """Report server state and required OpenAPI configuration."""
        return {
            "status": "ok",
            "transport": "streamable-http",
            "auth": "aksk",
            "configured": hiagent_config.is_configured,
            "top_host_configured": bool(hiagent_config.top_host),
            "account_id_configured": bool(hiagent_config.account_id),
            "access_key_configured": bool(hiagent_config.access_key_id),
            "secret_key_configured": bool(hiagent_config.secret_access_key),
            "region": hiagent_config.region,
            "service": hiagent_config.service,
        }

    @mcp.tool()
    def list_apps(
        page_number: int = 1,
        page_size: int = 20,
        app_name: str | None = None,
        workspace_ids: list[str] | None = None,
        start_time: str = "1970-01-01T00:00:00Z",
        end_time: str | None = None,
    ) -> dict[str, object]:
        """List HiAgent apps visible to the AK/SK identity."""
        return list_apps_handler(
            openapi_client,
            page_number=page_number,
            page_size=page_size,
            app_name=app_name,
            workspace_ids=workspace_ids,
            start_time=start_time,
            end_time=end_time,
        )

    @mcp.tool()
    def list_workflows(
        workspace_id: str,
        page_number: int = 1,
        page_size: int = 20,
        name_search: str | None = None,
    ) -> dict[str, object]:
        """List workflows in a HiAgent workspace."""
        return list_workflows_handler(
            openapi_client,
            workspace_id=workspace_id,
            page_number=page_number,
            page_size=page_size,
            name_search=name_search,
        )

    @mcp.tool()
    def get_workflow(
        workspace_id: str,
        workflow_id: str,
    ) -> dict[str, object]:
        """Get one workflow, including its nodes and links."""
        return get_workflow_handler(
            openapi_client,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
        )

    return mcp
```

- [ ] **Step 4: Run server and handler tests**

Run:

```bash
cd server/mcp_server_hiagent
uv run pytest tests/test_server.py tests/test_tools.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit the FastMCP registration slice**

```bash
git add server/mcp_server_hiagent/src/mcp_server_hiagent/server.py \
  server/mcp_server_hiagent/tests/test_server.py
git commit -m "feat: expose initial MCP tools [Meego-7358746283]"
```

### Task 3: Document the Tool Contract

**Files:**
- Modify: `server/mcp_server_hiagent/README.md`

- [ ] **Step 1: Replace the single-tool section**

Document all four tools and state that a private Top endpoint may be reached
through an operator-managed tunnel during development:

```markdown
## Tools

- `health_check`: reports MCP server and OpenAPI configuration state.
- `list_apps`: lists visible apps with paging, name, workspace, and creation
  time filters.
- `list_workflows`: lists workflows in a required workspace.
- `get_workflow`: returns one workflow, including nodes and links.

All business tools call HiAgent Platform OpenAPI with AK/SK. They do not call
Agent API and do not accept API keys.

For development against a Top Server that is only reachable inside the
deployment network, forward a local port to a Kubernetes node's Top NodePort
and set `HIAGENT_TOP_HOST` to the local forwarding address. The tunnel is an
operator setup step and is not created or managed by this MCP server.
```

- [ ] **Step 2: Check Markdown and repository diff**

Run:

```bash
git diff --check
git diff -- server/mcp_server_hiagent/README.md
```

Expected: no whitespace errors; only the intended tool documentation changes.

- [ ] **Step 3: Commit documentation**

```bash
git add server/mcp_server_hiagent/README.md
git commit -m "docs: document initial MCP tools [Meego-7358746283]"
```

### Task 4: Run the Full Local Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run every unit test**

```bash
cd server/mcp_server_hiagent
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Compile the package**

```bash
uv run python -m compileall -q src tests
```

Expected: exit code 0.

- [ ] **Step 3: Verify the FastMCP tool catalog**

```bash
uv run python -c 'import asyncio; from mcp_server_hiagent.server import create_mcp_server; print([tool.name for tool in asyncio.run(create_mcp_server().list_tools())])'
```

Expected:

```text
['health_check', 'list_apps', 'list_workflows', 'get_workflow']
```

### Task 5: Verify Against the Real Deployment Through SSH

**Files:**
- Verify only.

- [ ] **Step 1: Open the temporary Top tunnel**

Run in a dedicated terminal:

```bash
ssh -NT -L 33040:<CLUSTER_NODE_IP>:30040 root@<DEPLOY_HOST>
```

Expected: the SSH process remains running and
`curl -i http://127.0.0.1:33040/healthz?type=readiness` returns HTTP 200.

- [ ] **Step 2: Export runtime configuration without writing credentials**

```bash
export HIAGENT_TOP_HOST=http://127.0.0.1:33040
export HIAGENT_ACCOUNT_ID=1000000000
export HIAGENT_REGION=cn-north-1
export HIAGENT_SERVICE=app
read -r HIAGENT_ACCESS_KEY_ID
read -rs HIAGENT_SECRET_ACCESS_KEY
export HIAGENT_ACCESS_KEY_ID HIAGENT_SECRET_ACCESS_KEY
```

Expected: credentials exist only in the current process environment.

- [ ] **Step 3: Start the streamable HTTP server**

```bash
cd server/mcp_server_hiagent
uv run mcp-server-hiagent --transport streamable-http --host 127.0.0.1 --port 8000
```

Expected: FastMCP listens at `http://127.0.0.1:8000/mcp`.

- [ ] **Step 4: Call the MCP tools over `/mcp`**

Run from another terminal inheriting the same environment:

```python
import asyncio

from fastmcp import Client


async def main() -> None:
    async with Client("http://127.0.0.1:8000/mcp") as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools])
        apps = await client.call_tool("list_apps", {"page_size": 1})
        print(apps)


asyncio.run(main())
```

Execute with `uv run python` and standard input. Expected: all four tool names
are listed and `list_apps` returns `ResponseMetadata.Action=ListApp` without an
authentication or signature error.

- [ ] **Step 5: Complete the workflow chain when data exists**

Take the first `WorkspaceID` returned by `list_apps`, call
`list_workflows(workspace_id, page_size=1)`, then call
`get_workflow(workspace_id, workflow_id)` for its first item. Expected:
`ResponseMetadata.Action` is respectively `ListWorkflows` and `GetWorkflow`.
If the environment contains no workflows, retain the successful empty
`ListWorkflows` response as the integration result.

- [ ] **Step 6: Stop the MCP process and SSH tunnel**

Expected: ports `8000` and `33040` no longer have listener processes created by
this verification.

### Task 6: Final Repository Check

**Files:**
- Verify only.

- [ ] **Step 1: Check for accidental credentials**

```bash
git grep -n -E 'HIAK[A-Za-z0-9]{20,}|SECRET_ACCESS_KEY=.+' -- . \
  ':!docs/superpowers/plans/2026-08-06-initial-openapi-tools.md'
```

Expected: no real credential matches.

- [ ] **Step 2: Check the final diff and status**

```bash
git diff --check
git status --short
git log --oneline -5
```

Expected: no whitespace errors, no untracked implementation files, and all
feature commits contain `Meego-7358746283`.
