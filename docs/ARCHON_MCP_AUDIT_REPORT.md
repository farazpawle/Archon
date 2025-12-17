# Archon MCP Server Implementation Audit Report

**Date:** December 16, 2025
**Auditor:** Senior DevOps Engineer (AI Agent)
**Subject:** Comprehensive Audit of Archon MCP Server Architecture & Implementation

## 1. Executive Summary
The Archon MCP server is currently architected as a lightweight microservice that delegates heavy lifting to the main `archon-server` via HTTP. While this design effectively reduces container size and resource usage, the current implementation has critical vulnerabilities regarding transport flexibility and protocol integrity. The proposed "Hybrid Transport" plan addresses the primary need for local agent support (Stdio), but strict implementation safeguards are required to prevent protocol corruption and ensure connection stability.

## 2. Architecture & Data Flow Analysis

### 2.1 System Architecture
The system follows a **Hub-and-Spoke Microservices Pattern**:
-   **Hub**: `archon-server` (FastAPI + Supabase) - Handles business logic, DB access, and heavy compute.
-   **Spoke**: `archon-mcp` (FastMCP) - Acts as a protocol translator (JSON-RPC <-> HTTP).
-   **Spoke**: `archon-agents` (ML Service) - Handles embeddings/reranking (optional).

### 2.2 Data Flow Workflow
**Scenario: User asks "Search for vector functions"**

1.  **Ingestion (Protocol Layer)**
    *   **Stdio Mode**: Client writes JSON-RPC request to `stdin`.
    *   **SSE Mode**: Client sends HTTP POST to `/mcp/messages`.
2.  **Routing (MCP Layer)**
    *   `FastMCP` parses the request and routes it to the `rag_search_knowledge_base` tool.
3.  **Delegation (Service Layer)**
    *   Tool invokes `MCPServiceClient.search()`.
    *   Client constructs HTTP POST request to `http://archon-server:8181/api/rag/query`.
4.  **Execution (Business Layer)**
    *   `archon-server` receives request, queries Supabase `vectors` table.
    *   Results are returned as JSON.
5.  **Response (Protocol Layer)**
    *   `MCPServiceClient` receives JSON response.
    *   Tool formats it for MCP (TextContent).
    *   **Stdio**: `FastMCP` writes JSON-RPC response to `stdout`.
    *   **SSE**: `FastMCP` pushes event to client stream.

## 3. Communication Architecture Mapping

| Source | Destination | Protocol | Criticality | Timeout Risk |
| :--- | :--- | :--- | :--- | :--- |
| **Client** | **MCP Server** | JSON-RPC (Stdio/SSE) | **High** | Client-side timeout (typ. 60s) |
| **MCP Server** | **Archon Server** | HTTP/1.1 (Internal) | **High** | `httpx` read timeout (300s) |
| **MCP Server** | **Agents Service** | HTTP/1.1 (Internal) | Medium | Service availability check |
| **Archon Server** | **Supabase** | Postgres/HTTP | **High** | DB connection pool exhaustion |

## 4. Vulnerability Assessment & Risk Analysis

### 4.1 Critical Vulnerabilities

| ID | Vulnerability | Severity | Description |
| :--- | :--- | :--- | :--- |
| **V-01** | **Protocol Corruption (Stdio)** | **Critical** | In Stdio mode, `stdout` is the data channel. Any library (e.g., `uvicorn`, `httpx`) printing logs/warnings to `stdout` will corrupt the JSON-RPC stream, causing immediate client disconnection. |
| **V-02** | **Zombie Processes** | High | In Stdio mode, if the parent process (IDE) dies without sending `SIGTERM`, the Docker container may persist, consuming resources. |
| **V-03** | **Initialization Race Condition** | Medium | The global `_initialization_lock` logic is complex. While intended for SSE, it adds unnecessary overhead for Stdio mode which is single-connection by design. |
| **V-04** | **Hardcoded Transport** | High | Current `mcp_server.py` hardcodes `transport="streamable-http"`, making Stdio usage impossible without code changes. |

### 4.2 Potential Points of Failure

1.  **Logging Configuration**: The current `logging.basicConfig` writes to `sys.stdout`. This **MUST** be changed for Stdio mode.
2.  **Environment Variables**: The server crashes if `ARCHON_MCP_PORT` is missing. It should have a sensible default.
3.  **Service Discovery**: Reliance on `API_SERVICE_URL` env var. If misconfigured, all tools fail.

## 5. Recommendations for Stability

### 5.1 Immediate Fixes (Pre-Deployment)
1.  **Implement Hybrid Transport Logic**: As per `HYBRID_TRANSPORT_PLAN.md`, strictly separate Stdio and SSE initialization paths.
2.  **Monkey-Patch Stdout**: In Stdio mode, explicitly redirect `sys.stdout` to `sys.stderr` for all code *except* the MCP transport writer. This catches rogue `print()` statements from third-party libraries.
    ```python
    if transport == "stdio":
        sys.stdout = sys.stderr # Redirect all prints to stderr
        # FastMCP will need to write to the *original* stdout file descriptor
    ```
    *(Note: FastMCP handles this internally usually, but explicit safety is better)*.

### 5.2 Operational Best Practices
1.  **Health Check Monitoring**: Use the `/health` endpoint to monitor `archon-server` connectivity.
2.  **Log Aggregation**: In Docker, ensure logs sent to `stderr` are correctly captured by the logging driver (e.g., AWS CloudWatch, ELK).
3.  **Timeout Alignment**: Ensure the Client (Claude), MCP Server, and Archon Server timeouts are aligned.
    *   Client: 60s (default) -> Increase if possible.
    *   MCP `httpx`: 300s (current) -> Good.
    *   Archon Server: Ensure `uvicorn` timeout is > 300s.

## 6. Implementation Checklist

- [ ] **Refactor `mcp_server.py`**:
    - [ ] Read `TRANSPORT` env var.
    - [ ] Configure logging based on transport (Stderr for Stdio, Stdout for SSE).
    - [ ] Initialize `FastMCP` with correct transport string.
- [ ] **Update `Dockerfile`**:
    - [ ] Ensure `python -u` (unbuffered) is used or `PYTHONUNBUFFERED=1` is set (Already present).
- [ ] **Verify Service Client**:
    - [ ] Confirm `httpx` client reuses connections (Performance).
- [ ] **Test Stdio Mode**:
    - [ ] Run `docker run -i ...` and pipe raw JSON-RPC.
    - [ ] Verify no "garbage" text appears in output.
- [ ] **Test SSE Mode**:
    - [ ] Run `docker run -p ...` and connect via SSE client.
- [ ] **Documentation**:
    - [ ] Add `DEPLOYMENT.md` with specific run commands.

## 7. Conclusion
The current architecture is sound for a microservices-based MCP server, but the implementation needs the planned "Hybrid Transport" refactor to be production-ready for local agents. By strictly isolating logging output and implementing the transport switch, the system will meet all user requirements for flexibility and stability.
