#!/usr/bin/env python
"""Check available tools from MCP server."""

import json
import httpx

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}

response = httpx.post("http://localhost:8051/mcp", json=payload, timeout=10)
data = response.json()
tools = data.get("result", {}).get("tools", [])

print(f"Total tools available: {len(tools)}\n")
for tool in tools:
    print(f"✓ {tool['name']}")
