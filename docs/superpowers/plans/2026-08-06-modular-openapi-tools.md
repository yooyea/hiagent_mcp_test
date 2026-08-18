# Modular OpenAPI Tools Implementation Plan

> 状态：当前实现的结构依据（模块化 `tools/` 布局），落地于 `server/mcp_server_hiagent/compatibility/hiagent-v3.1`。工具集已演进为知识引擎工具，模块化组织方式仍然适用。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic OpenAPI tool file with App and Workflow modules while preserving the public MCP contract.

**Architecture:** Shared client typing and pagination validation live in `tools/_common.py`. Each business module owns its handlers and FastMCP registration function. `server.py` only constructs dependencies and invokes module registration.

**Tech Stack:** Python 3.11, FastMCP 3.x, pytest, HiAgent Platform OpenAPI.

---

### Task 1: Migrate Source and Test Ownership

**Files:**
- Move: `server/mcp_server_hiagent/src/mcp_server_hiagent/tools.py`
  to `server/mcp_server_hiagent/src/mcp_server_hiagent/tools/app.py`
- Move: `server/mcp_server_hiagent/tests/test_tools.py`
  to `server/mcp_server_hiagent/tests/tools/test_app.py`

- [ ] Create the two destination directories.
- [ ] Use `git mv` for both tracked files.
- [ ] Run `git status --short` and verify both entries are recorded as renames.

### Task 2: Extract Shared Tool Infrastructure

**Files:**
- Create: `server/mcp_server_hiagent/src/mcp_server_hiagent/tools/_common.py`
- Create: `server/mcp_server_hiagent/src/mcp_server_hiagent/tools/__init__.py`

- [ ] Move `OpenAPIClient`, `OPENAPI_VERSION`, `OPENAPI_SERVICE`, and
  `_validate_pagination` from `app.py` into `_common.py`.
- [ ] Export `OpenAPIClient`, `register_app_tools`, and
  `register_workflow_tools` from `tools/__init__.py`.
- [ ] Keep `_validate_pagination` private to the tools package.

Expected `_common.py` interface:

```python
from collections.abc import Mapping
from typing import Protocol


OPENAPI_VERSION = "2023-08-01"
OPENAPI_SERVICE = "app"


class OpenAPIClient(Protocol):
    def call(
        self,
        *,
        action: str,
        body: Mapping[str, object] | None = None,
        version: str = OPENAPI_VERSION,
        service: str | None = None,
        timeout_seconds: float = 30,
    ) -> dict[str, object]:
        raise NotImplementedError


def validate_pagination(page_number: int, page_size: int) -> None:
    if page_number < 1:
        raise ValueError("page_number must be at least 1")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
```

### Task 3: Complete the App Module

**Files:**
- Modify: `server/mcp_server_hiagent/src/mcp_server_hiagent/tools/app.py`
- Modify: `server/mcp_server_hiagent/tests/tools/test_app.py`

- [ ] Retain only `list_apps`, its UTC default helper, and App constants in
  `app.py`.
- [ ] Add:

```python
def register_app_tools(mcp: FastMCP, client: OpenAPIClient) -> None:
    @mcp.tool(name="list_apps")
    def list_apps_tool(
        page_number: int = 1,
        page_size: int = 20,
        app_name: str | None = None,
        workspace_ids: list[str] | None = None,
        start_time: str = DEFAULT_START_TIME,
        end_time: str | None = None,
    ) -> dict[str, object]:
        return list_apps(
            client,
            page_number=page_number,
            page_size=page_size,
            app_name=app_name,
            workspace_ids=workspace_ids,
            start_time=start_time,
            end_time=end_time,
        )
```

- [ ] Retain only App tests in `test_app.py`.
- [ ] Run:

```bash
cd server/mcp_server_hiagent
uv run pytest tests/tools/test_app.py -q
```

Expected: App request mapping, defaults, and pagination tests pass.

### Task 4: Create the Workflow Module

**Files:**
- Create: `server/mcp_server_hiagent/src/mcp_server_hiagent/tools/workflow.py`
- Create: `server/mcp_server_hiagent/tests/tools/test_workflow.py`

- [ ] Move `list_workflows` and `get_workflow` behavior into `workflow.py`.
- [ ] Add:

```python
def register_workflow_tools(mcp: FastMCP, client: OpenAPIClient) -> None:
    @mcp.tool(name="list_workflows")
    def list_workflows_tool(
        workspace_id: str,
        page_number: int = 1,
        page_size: int = 20,
        name_search: str | None = None,
    ) -> dict[str, object]:
        return list_workflows(
            client,
            workspace_id=workspace_id,
            page_number=page_number,
            page_size=page_size,
            name_search=name_search,
        )

    @mcp.tool(name="get_workflow")
    def get_workflow_tool(
        workspace_id: str,
        workflow_id: str,
    ) -> dict[str, object]:
        return get_workflow(
            client,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
        )
```

- [ ] Move the exact request-body assertions into `test_workflow.py`.
- [ ] Add workflow pagination validation coverage.
- [ ] Run:

```bash
cd server/mcp_server_hiagent
uv run pytest tests/tools/test_workflow.py -q
```

Expected: Workflow request mapping and validation tests pass.

### Task 5: Replace Server-Level Tool Definitions

**Files:**
- Modify: `server/mcp_server_hiagent/src/mcp_server_hiagent/server.py`
- Verify: `server/mcp_server_hiagent/tests/test_server.py`

- [ ] Replace business handler imports with:

```python
from mcp_server_hiagent.tools import (
    OpenAPIClient,
    register_app_tools,
    register_workflow_tools,
)
```

- [ ] Delete the nested business tool functions from `create_mcp_server`.
- [ ] Register modules after `health_check`:

```python
register_app_tools(mcp, openapi_client)
register_workflow_tools(mcp, openapi_client)
```

- [ ] Run:

```bash
cd server/mcp_server_hiagent
uv run pytest tests/test_server.py tests/tools -q
```

Expected tool names:

```text
health_check
list_apps
list_workflows
get_workflow
```

### Task 6: Local and Real Verification

**Files:**
- Verify only.

- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run python -m compileall -q src tests`.
- [ ] Start a temporary SSH forward from local `33040` to a cluster node's
  Top NodePort `30040`.
- [ ] Start the MCP server on an unused local port.
- [ ] Through FastMCP Client, call `list_apps`, then `list_workflows`, then
  `get_workflow`.
- [ ] Verify `ResponseMetadata.Action` remains `ListApp`, `ListWorkflows`, and
  `GetWorkflow`.
- [ ] Stop the MCP server and SSH tunnel.
- [ ] Run the credential scan and verify the Git worktree contains only the
  intended modularization changes.

### Task 7: Commit and Push

- [ ] Commit the design and implementation plan with
  `Meego-7358746283`.
- [ ] Commit the source and test migration with `Meego-7358746283`.
- [ ] Push `feat/scaffold-hiagent-mcp-server`.
