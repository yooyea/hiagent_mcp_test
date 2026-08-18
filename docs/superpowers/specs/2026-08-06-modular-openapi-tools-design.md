# Modular OpenAPI Tools Design

> 状态：当前实现的结构依据（模块化 `tools/` 布局），落地于 `server/mcp_server_hiagent/compatibility/hiagent-v3.1`。注意：本文示例中的 App/Workflow 工具已被知识引擎工具（`call_knowledge_engine_tool` / `list_datasets` / `get_dataset`）取代，模块化组织方式仍然适用。

## Goal

Replace the single `tools.py` module with business-domain modules that match
HiAgent OpenAPI and IDL ownership boundaries.

## Package Structure

```text
mcp_server_hiagent/
├── tools/
│   ├── __init__.py
│   ├── _common.py
│   ├── app.py
│   └── workflow.py
└── server.py
```

Tests follow the same ownership:

```text
tests/
└── tools/
    ├── test_app.py
    └── test_workflow.py
```

## Responsibilities

### `tools/_common.py`

- Defines the `OpenAPIClient` protocol.
- Owns shared OpenAPI version and signing-service constants.
- Owns pagination validation used by multiple modules.
- Does not register MCP tools or contain business actions.

### `tools/app.py`

- Owns App OpenAPI request mapping.
- Implements the `list_apps` handler.
- Registers the public `list_apps` MCP tool through
  `register_app_tools(mcp, client)`.

### `tools/workflow.py`

- Owns Workflow OpenAPI request mapping.
- Implements `list_workflows` and `get_workflow`.
- Registers both public MCP tools through
  `register_workflow_tools(mcp, client)`.

### `tools/__init__.py`

- Exposes module registration functions and the shared client protocol.
- Does not re-export business handlers; callers import handlers from their
  owning module.

### `server.py`

- Builds the configured `HiAgentOpenAPIClient`.
- Registers `health_check`.
- Calls each module registration function.
- Contains no OpenAPI action names or request-body construction.

## Registration Contract

Each business module exposes one registration function named
`register_<module>_tools(mcp: FastMCP, client: OpenAPIClient) -> None`.

The registered MCP name remains stable (`list_apps`, `list_workflows`, and
`get_workflow`) even though implementation functions move between files.

## Migration

Use `git mv` for both source and test migration:

- `tools.py` moves to `tools/app.py` before being split.
- `test_tools.py` moves to `tests/tools/test_app.py` before workflow tests are
  extracted.

No product behavior, request schema, authentication method, environment
variable, or MCP transport changes.

## Verification

- Module tests continue to assert exact OpenAPI action and request bodies.
- Registration tests assert the unchanged public MCP tool catalog.
- The complete test suite and package compilation pass.
- A real streamable HTTP MCP client calls all three business tools through the
  SSH tunnel and receives the expected OpenAPI actions.
