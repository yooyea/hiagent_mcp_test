# mcp-server-hiagent

HiAgent MCP Server internal implementation repository.

This repository is the source of truth for the HiAgent MCP Server implementation and
the OpenAPI-to-MCP generation workflow. The public release artifact is versioned
by HiAgent compatibility path so customer `uvx` subdirectory configs remain stable.

Initial product constraints:

- Distribution: `uvx --from git+https://code.byted.org/epscp/mcp-server-hiagent#subdirectory=server/mcp_server_hiagent/compatibility/hiagent-v3.1`
- Transport: `streamable-http` only
- Authentication: AK/SK only
- Region: defaults to `cn-north-1` and participates in AK/SK V4 signing
- Latest alias: not provided; customers must choose an explicit HiAgent
  compatibility directory.
