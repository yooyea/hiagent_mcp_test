# Initial HiAgent OpenAPI Tools Design

> 状态：历史设计（未采用为当前实现），仅留档。当前实现见 `server/mcp_server_hiagent/compatibility/hiagent-v3.1`（modular 结构），其工具集已演进为知识引擎工具（`call_knowledge_engine_tool` / `list_datasets` / `get_dataset`），不再是本文所述的 App/Workflow 工具。

## Goal

Expose the first useful, read-only HiAgent Platform OpenAPI actions as explicit
MCP tools. Product authentication remains AK/SK only. Development integration
tests reach the private Top Server through a temporary SSH tunnel; the tunnel is
not part of the product runtime.

## Scope

The first batch contains three tools:

1. `list_apps`
   - OpenAPI action: `ListApp`
   - Version: `2023-08-01`
   - Service: `app`
   - Inputs: page number, page size, optional app name, optional workspace IDs,
     optional RFC3339 start and end times.
   - Defaults: page 1, 20 items, start at `1970-01-01T00:00:00Z`, end at the
     current UTC time.
2. `list_workflows`
   - OpenAPI action: `ListWorkflows`
   - Version: `2023-08-01`
   - Service: `app`
   - Inputs: required workspace ID, page number, page size, optional name
     search.
3. `get_workflow`
   - OpenAPI action: `GetWorkflow`
   - Version: `2023-08-01`
   - Service: `app`
   - Inputs: required workspace ID and workflow ID.

Write actions, Agent API endpoints, API key authentication, and a generic raw
OpenAPI action tool are outside this change.

## Structure

- Keep signing, transport, and response parsing in `HiAgentOpenAPIClient`.
- Add small handler functions that translate typed MCP parameters into the
  exact OpenAPI request bodies.
- `create_mcp_server` creates one configured client and registers the handlers
  as FastMCP tools.
- Permit client injection into `create_mcp_server` so unit tests do not use the
  network or credentials.
- Return the complete successful OpenAPI response, including
  `ResponseMetadata` and `Result`. Existing `OpenAPIError` behavior remains the
  single error contract.

## Request Rules

- Page numbers must be at least 1.
- Page sizes must be between 1 and 100.
- `ListApp.Filter` always includes `StartTime` and `EndTime`, because the real
  generated Thrift model requires both fields even though the top-level filter
  is optional.
- `ListWorkflows` and `GetWorkflow` always include `WorkspaceID`.
- Empty optional filters are omitted except where the backend requires an
  explicit filter object.

## Verification

Unit tests verify tool registration, action names, versions, services, request
bodies, defaults, and page validation with a fake client.

The real-environment check uses a temporary local forward:

```text
127.0.0.1:33040
  -> SSH root@deployment-host
  -> Kubernetes node:30040
  -> top-server:8000
```

With `HIAGENT_TOP_HOST=http://127.0.0.1:33040`, the MCP server must start, expose
all three tools through `/mcp`, and complete real AK/SK calls for every tool for
which the environment contains suitable app, workspace, and workflow data. The
SSH tunnel is closed after verification.
