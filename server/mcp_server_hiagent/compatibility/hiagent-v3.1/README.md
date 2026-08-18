# HiAgent MCP Server

HiAgent MCP Server exposes selected HiAgent OpenAPI capabilities through the
Model Context Protocol.

## Scope

- Target HiAgent version: `3.1`
- Distribution: `uvx --from git+<repo>#subdirectory=server/mcp_server_hiagent/compatibility/hiagent-v3.1`
- Transport: `stdio` (default, for HiAgent STDIO plugin) or `streamable-http`
- Authentication: AK/SK only
- Credentials: environment variables
- Default region: `cn-north-1`
- Latest alias: not provided. Production clients should pin this explicit
  compatibility path.

`pip install`, Docker images, SSE, browser cookies, bearer tokens, and custom
Authorization headers are not supported product entrypoints.

## Credentials & Environment Variables

Credentials are supplied via **environment variables**. In HiAgent's MCP plugin
(STDIO transport), fill these in the plugin "环境变量 / Environment variables"
table (mark AK/SK as sensitive).

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `HIAGENT_TOP_HOST` | Yes | - | HiAgent Platform API (`volc-top`) address, incl. scheme and port. Default NodePort is `30040`. Not the web address or Agent API address. |
| `HIAGENT_ACCESS_KEY_ID` | Yes | - | HiAgent AccessKey ID. |
| `HIAGENT_SECRET_ACCESS_KEY` | Yes | - | HiAgent SecretAccessKey. |
| `HIAGENT_ACCOUNT_ID` | No | `1000000000` | Main account id sent as the `X-Account-Id` query parameter. |
| `HIAGENT_REGION` | No | `cn-north-1` | Region used in AK/SK V4 signing (not a network address). |
| `FASTMCP_CHECK_FOR_UPDATES` | Recommended | - | Set to `off`. FastMCP's startup update check otherwise makes an outbound request and can crash the process on startup (including under STDIO). **Add this to the HiAgent env table too.** |

Server-only runtime parameters (streamable-http transport):

| Variable | Default | Description |
| --- | --- | --- |
| `MCP_SERVER_HOST` | `127.0.0.1` | Bind host. |
| `MCP_SERVER_PORT` | `8000` | Bind port. |
| `STREAMABLE_HTTP_PATH` | `/mcp` | Streamable HTTP endpoint path. |

## Run

### HiAgent STDIO plugin (recommended)

In the HiAgent "更新 MCP 插件" dialog: transport = **STDIO**, command:

```bash
uvx --from "git+<repo>#subdirectory=server/mcp_server_hiagent/compatibility/hiagent-v3.1" mcp-server-hiagent
```

(defaults to `--transport stdio`). Then add the environment variables above in
the plugin's env table. The repository must be reachable by `uvx` (public, or
authenticated git URL).

### Local streamable-http (optional)

```bash
HIAGENT_TOP_HOST="http://<top-host>:30040" \
HIAGENT_ACCESS_KEY_ID="<your-ak>" \
HIAGENT_SECRET_ACCESS_KEY="<your-sk>" \
FASTMCP_CHECK_FOR_UPDATES=off \
uvx --from "git+<repo>#subdirectory=server/mcp_server_hiagent/compatibility/hiagent-v3.1" \
  mcp-server-hiagent --transport streamable-http --host 127.0.0.1 --port 8000
```

## Tools

- `health_check`: reports MCP server and OpenAPI configuration state.
- `list_datasets`: lists datasets (knowledge bases) in a required workspace, so
  callers can obtain the `DatasetIDs` required by the knowledge engine.
- `get_dataset`: returns one dataset, including default retrieval parameters.
- `call_knowledge_engine_tool`: calls the HiAgent knowledge engine over one or
  more datasets. Only `tool_name="knowledge_search"` is supported at present
  (retrieves knowledge chunks for the given queries). Other known sub-tools
  (`list_knowledge_chunks`, `grep_chunks`, `get_doc_info`, `wiki_search`,
  `wiki_read_page`, `wiki_read_source_doc`) are recognized but not yet
  supported and are rejected.

All business tools call HiAgent Platform OpenAPI with AK/SK. They do not call
Agent API and do not accept API keys.

## Private Top Development Access

For development against a Top Server that is only reachable inside the
deployment network, forward a local port to a Kubernetes node's Top NodePort
and set `HIAGENT_TOP_HOST` to the local forwarding address. The tunnel is an
operator setup step and is not created or managed by this MCP server.
