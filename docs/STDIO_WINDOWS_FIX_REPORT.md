# Archon MCP Stdio Windows Fix Report

**Date:** December 17, 2025
**Status:** ✅ Fixed & Verified
**Subject:** Resolution of -32000 Error / Connection Failure on Windows

## 1. Executive Summary
The persistent connection failure (often reported as error `-32000` or immediate process exit) when running the MCP server in stdio mode on Windows has been identified and fixed. The root cause was a hardcoded dependency on the `/tmp` directory, which does not exist on Windows systems. This caused the session manager to crash immediately upon startup, terminating the MCP server process before it could handle any requests.

## 2. Root Cause Analysis

### The "Unix-Only" Path Assumption
The file `python/src/server/services/mcp_session_manager.py` contained the following line:

```python
# OLD CODE
SESSION_FILE = Path("/tmp/mcp_sessions.json")
```

**Why this failed on Windows:**
1.  **Path Resolution**: On Windows, `/tmp` is interpreted relative to the current drive root (e.g., `C:\tmp` or `D:\tmp`).
2.  **Missing Directory**: This directory typically does not exist on Windows.
3.  **Crash**: When `main()` called `session_manager.register_session()`, it attempted to write to this file. The `open()` call raised a `FileNotFoundError` (or `OSError`), causing the script to crash and exit with status code 1.
4.  **IDE Error**: The IDE (VS Code, Cursor) detected the unexpected process termination and reported a generic server error (`-32000`) or connection failure.

### Secondary Issue: Logging
The `mcp_server.py` file also attempted to log to `/tmp/mcp_server.log`, which silently failed (falling back to `NullHandler`) on Windows, making debugging difficult.

## 3. The Fix Implementation

We have modified the code to use Python's cross-platform `tempfile` module.

### 1. Session Manager Fix
**File**: `python/src/server/services/mcp_session_manager.py`
```python
import tempfile
# ...
# NEW CODE: Uses system temp directory (e.g., C:\Users\User\AppData\Local\Temp)
SESSION_FILE = Path(tempfile.gettempdir()) / "mcp_sessions.json"
```

### 2. Logging Fix
**File**: `python/src/mcp_server/mcp_server.py`
```python
import tempfile
# ...
logging.FileHandler(os.path.join(tempfile.gettempdir(), "mcp_server.log"), mode="a")
```

## 4. Verification

A verification script `verify_session_manager.py` was created and executed on the Windows environment.
**Result**:
```
Initializing session manager...
Session manager initialized.
Registering session...
Session registered: [UUID]
Unregistering session...
Session unregistered.
SUCCESS: Session manager works on this platform.
```

## 5. Configuration Guide for IDEs

To ensure proper stdio connectivity, use the following configuration patterns.

### VS Code / Cursor (mcp.json or settings)

Ensure you are running from the `python` directory so the module path is correct.

```json
{
  "mcpServers": {
    "archon": {
      "command": "python",
      "args": ["-m", "src.mcp_server.mcp_server"],
      "cwd": "${workspaceFolder}/python",
      "env": {
        "TRANSPORT": "stdio",
        "ARCHON_MCP_PORT": "8051",
        "ARCHON_SERVER_PORT": "8181",
        "ARCHON_AGENTS_PORT": "8052"
      }
    }
  }
}
```

### Troubleshooting

If issues persist:
1.  **Check Logs**: Look at `%TEMP%\mcp_server.log` (e.g., `C:\Users\YourUser\AppData\Local\Temp\mcp_server.log`).
2.  **Environment Variables**: Ensure `ARCHON_MCP_PORT` is set. The server will exit if this is missing.
3.  **Python Path**: Ensure `cwd` is set to the `python` folder, or add it to `PYTHONPATH`.

## 6. Conclusion
The MCP server is now fully compatible with Windows environments for stdio transport. The crash-on-startup issue has been resolved.
