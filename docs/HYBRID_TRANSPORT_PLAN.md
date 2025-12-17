# Archon Hybrid Transport Architecture Plan

**Date:** December 16, 2025
**Status:** Approved for Implementation

## 1. Executive Summary
This document outlines the architectural plan to transition the Archon MCP server to a **Runtime-Configurable Hybrid Transport System**. This change allows the same Docker image to support both **Stdio** (for local agents like Claude Desktop/VS Code) and **HTTP/SSE** (for remote clients/web UIs) protocols, selectable via environment variables.

## 2. Context & Problem Definition
- **Current State**: The server is hardcoded to use `streamable-http` transport. Logging writes to `stdout`, which is standard for Docker but fatal for `stdio` transport (corrupts the JSON-RPC stream).
- **The Need**: Users require the flexibility to run Archon natively or via Docker piping for local tools, while maintaining the ability to deploy as a microservice.
- **The Solution**: Decouple the transport layer from the application logic and enforce strict I/O isolation based on the selected mode.

## 3. Architecture: The "Hybrid Transport" Pattern

The core innovation is a runtime configuration switch within the container entry point that determines the transport mode and logging strategy.

### Component Diagram

```mermaid
graph TD
    A[Docker Container / Native Process] --> B{Entry Point (mcp_server.py)}
    B -- TRANSPORT=sse --> C[HTTP/SSE Server]
    B -- TRANSPORT=stdio --> D[Stdio Server]
    C --> E[MCP Tools]
    D --> E
    
    subgraph Logging Strategy
    C -- Logs --> stdout/stderr
    D -- Logs --> stderr ONLY
    end
```

## 4. Critical Implementation Details

### A. Logging Isolation (The "Stdio Safety" Rule)
**Risk**: In `stdio` mode, `stdout` is the data channel. Any log message sent to `stdout` (even from third-party libs like `uvicorn`) will break the JSON-RPC protocol.
**Implementation**:
- **Stdio Mode**: 
  1. Force all logging handlers to write exclusively to `sys.stderr`.
  2. **Mandatory**: Monkey-patch `sys.stdout = sys.stderr` at the start of `main()` (before any imports if possible) to redirect all rogue `print()` calls.
- **SSE Mode**: Allow logging to `sys.stdout` (standard Docker practice).

### B. Transport Switching Logic
The `main()` function in `mcp_server.py` will act as a dispatcher:
```python
transport = os.getenv("TRANSPORT", "sse").lower()

if transport == "stdio":
    # Configure logging to stderr
    logging.basicConfig(handlers=[logging.StreamHandler(sys.stderr)], ...)
    # Run stdio server
    mcp.run(transport="stdio")
else:
    # Configure logging to stdout
    logging.basicConfig(handlers=[logging.StreamHandler(sys.stdout)], ...)
    # Run SSE server
    mcp.run(transport="streamable-http")
```

## 5. Deployment Strategy

### Mode 1: HTTP/SSE (Default)
**Use Case**: Connecting to remote clients, web UIs, or when port forwarding is preferred.
```bash
docker run -p 8051:8051 -e TRANSPORT=sse archon-mcp
```

### Mode 2: Stdio (The "Pipe" Mode)
**Use Case**: Local AI agents (Claude Desktop, Cursor) that spawn subprocesses.
**Crucial**: The `-i` (interactive) flag is required to keep `stdin` open.
```bash
docker run -i --rm -e TRANSPORT=stdio archon-mcp
```

## 6. Technical Audit & Risk Analysis

### Identified Risks & Preventive Measures

| Risk Category | Potential Problem | Preventive Measure |
|---------------|-------------------|--------------------|
| **Protocol Integrity** | Logs on `stdout` corrupting JSON-RPC stream. | **Strict I/O Isolation**: Enforce `stderr` logging in code. Monkey-patch `print` if necessary. |
| **Process Lifecycle** | Zombie processes if parent disconnects. | **Parent PID Monitoring**: In native mode, monitor PPID. In Docker, use `--rm` and handle signals correctly. |
| **Signal Handling** | `SIGINT` (Ctrl+C) killing the server unexpectedly. | **Signal Masking**: In stdio mode, ignore `SIGINT` and rely on `stdin` closure for termination. |
| **Path/Env Issues** | Native execution failing on Windows paths. | **Path Normalization**: Use `pathlib` exclusively. Validate environment variables on startup. |

## 7. Implementation Plan

### Task 1: Implement Hybrid Transport Logic
- Refactor `python/src/mcp_server/mcp_server.py`.
- **CRITICAL**: Implement `sys.stdout` redirection to `sys.stderr` for Stdio mode to catch third-party prints.
- Implement the dynamic logging configuration.
- Implement the transport selection logic.

### Task 2: Create Deployment Documentation
- Create `DEPLOYMENT.md`.
- Document the specific `docker run` commands for both modes.
- Add troubleshooting tips for common errors (e.g., forgetting `-i`).

## 8. Verification Plan
1.  **Unit Test**: Verify logging config respects `TRANSPORT` env var.
2.  **Integration Test (SSE)**: Run container, `curl http://localhost:8051/sse`.
3.  **Integration Test (Stdio)**: Run container, pipe JSON-RPC handshake to stdin, verify JSON response on stdout.
