#!/usr/bin/env python
"""Test schema generation for the fixed tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")

@mcp.tool()
async def test_manage_document(
    action: str,
    project_id: str,
    document_id: str | None = None,
    title: str | None = None,
    document_type: str | None = None,
    content: Any = None,
    tags: list[str] | None = None,
    author: str | None = None,
) -> str:
    """Test document tool with Any type."""
    return "success"

@mcp.tool()
async def test_manage_version(
    action: str,
    project_id: str,
    field_name: str = "docs",
    version_number: int | None = None,
    content: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> str:
    """Test version tool with default."""
    return "success"

print("Testing schema generation...")
try:
    # Try to get tools list which triggers schema generation
    print(f"Tools registered: {len(mcp._tool_manager._tools)}")
    for name in mcp._tool_manager._tools:
        print(f"  - {name}")
    print("✅ Schema generation successful!")
except Exception as e:
    print(f"❌ Schema generation failed: {e}")
    import traceback
    traceback.print_exc()
