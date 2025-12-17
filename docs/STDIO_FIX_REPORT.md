# Archon MCP Stdio Transport Analysis & Fix Report

**Date:** December 17, 2025
**Status:** ✅ Fixed & Verified
**Subject:** Resolution of -32001 Timeout Errors in Stdio Mode

## 1. Executive Summary
The "Request timed out (-32001)" error reported by users in VS Code, Cursor, and Kilo Code has been definitively traced to a critical design flaw in the `stdio` transport implementation. The server was explicitly redirecting `stdout` to `stderr` to "protect" the stream from logging noise, but this inadvertently redirected the MCP protocol's own JSON-RPC responses, causing the client to wait indefinitely.

**The fix has been applied and verified.** The server now initializes correctly in stdio mode with sub-second response times.

## 2. Root Cause Analysis

### The "Protection" That Broke the Protocol
The file `python/src/mcp_server/mcp_server.py` contained the following logic:

```python
# OLD CODE (Caused the bug)
if TRANSPORT == "stdio":
    sys.stdout = sys.stderr  # <--- THE CULPRIT
```

**Why this failed:**
1.  **MCP Protocol Requirement**: In `stdio` mode, the server **MUST** write its JSON-RPC responses (like the `initialize` result) to the process's standard output (`stdout`).
2.  **The Flaw**: By reassigning `sys.stdout = sys.stderr`, **ALL** writes to `sys.stdout`—including those from the MCP SDK itself—were sent to `stderr`.
3.  **The Result**: The client (VS Code/Cursor) listened on `stdout` but received nothing. It eventually timed out with error `-32001`.

### Secondary Issue: Environment Loading
The `.env` file loading logic was incorrect for native execution:
```python
# OLD CODE
project_root = Path(__file__).resolve().parent.parent  # Points to python/src
dotenv_path = project_root / ".env"
```
This failed to find the `.env` file in the repository root (`Archon/.env`), causing the server to start with missing configuration in some native scenarios.

## 3. The Fix Implementation

We have modified `python/src/mcp_server/mcp_server.py` to:

1.  **Remove Stdout Redirection**: The global `sys.stdout = sys.stderr` line has been removed. The MCP SDK is now free to write protocol messages to the real `stdout`.
2.  **Safe Logging**: We rely on the existing logging configuration (which uses `StreamHandler(sys.stderr)` in stdio mode) to keep logs off `stdout`.
3.  **Correct Env Loading**: The `.env` path resolution now correctly traverses up to the repository root.

## 4. Verification Results

We performed automated smoke tests using the official `mcp` Python client.

### Test 1: Timeout Reproduction (Before Fix)
*   **Command**: Spawn server in stdio mode, send `initialize` request.
*   **Result**: `RuntimeError: initialize() timed out after 10.0s`
*   **Status**: ❌ Failed (Confirmed bug)

### Test 2: Verification (After Fix)
*   **Command**: Spawn server in stdio mode, send `initialize` request.
*   **Result**: `initialized archon-mcp-server` (Immediate response)
*   **Status**: ✅ Passed

### Test 3: Full Functionality
*   **Command**: Initialize and list tools.
*   **Result**: `tool_count 16`
*   **Status**: ✅ Passed

## 5. Recommendations for Users

### For Docker Users (VS Code / Cursor)
You must rebuild the container for the fix to take effect:
```bash
docker compose build archon-mcp
docker compose up -d archon-mcp
```

### For Native Users (Kilo Code / Local Dev)
Ensure you are running the server with `uv` or your Python environment:
```bash
# Example for Kilo Code configuration
{
  "command": "uv",
  "args": ["run", "python", "-m", "src.mcp_server.mcp_server"],
  "env": {
    "TRANSPORT": "stdio",
    "ARCHON_MCP_PORT": "8051",
    ...
  }
}
```

## 6. Conclusion
The stdio transport is now fully functional. The design flaw has been corrected, and the server adheres to the MCP protocol specification for stdio communication. No further architectural changes are needed for this issue.
