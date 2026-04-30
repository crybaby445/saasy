# Future Features

## MCP Server Generator

Convert SaaS application API specs (OpenAPI/Swagger) and CLI command definitions into Model Context Protocol (MCP) servers automatically.

**Vision:** Given an OpenAPI spec or a set of CLI commands for a SaaS target, generate a fully functional MCP server that exposes those endpoints/commands as MCP tools. This would allow AI agents (including the saasy AI engine) to natively call into any SaaS platform through a standardized MCP interface — no custom connector needed.

**Why this matters:**
- Eliminates the need to write per-platform connectors manually
- Any SaaS with an OpenAPI spec becomes immediately usable as an AI tool
- Enables the saasy session AI to call target APIs directly as MCP tools during enumeration
- Generated MCP servers are reusable outside of saasy (e.g., in Claude Desktop, other agents)

**Inputs:**
- OpenAPI/Swagger spec (URL or file)
- CLI command manifest (structured YAML/JSON describing commands, flags, and outputs)

**Outputs:**
- A self-contained MCP server (Python, using the MCP SDK)
- Auto-generated tool definitions with parameter schemas derived from the spec
- Auth injection (API key, bearer token, basic auth) wired into generated tools
