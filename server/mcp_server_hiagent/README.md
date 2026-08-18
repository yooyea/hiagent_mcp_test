# HiAgent MCP Server Compatibility Paths

This directory intentionally does not contain a runnable MCP package.

Customers must choose an explicit HiAgent compatibility path:

```bash
uvx --from "git+https://code.byted.org/epscp/mcp-server-hiagent#subdirectory=server/mcp_server_hiagent/compatibility/hiagent-v3.1" \
  mcp-server-hiagent
```

There is no `latest` alias. The subdirectory path is part of the customer-facing
contract and must remain stable for each supported HiAgent release line.
