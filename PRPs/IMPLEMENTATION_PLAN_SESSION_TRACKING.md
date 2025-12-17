# Implementation Plan: Real-Time Session Tracking & Visualization

## 1. Executive Summary
This document outlines the implementation plan for adding a "Session Block" to the Archon MCP server. This feature will provide real-time visibility into connected clients, distinguishing between HTTP (SSE) and Stdio transport modes. The solution involves enhancing the backend session management, implementing connection interception, exposing a new internal API, and creating a frontend visualization component.

## 2. Architecture Design

### 2.1 Data Flow
1.  **Client Connection:**
    -   **IDE (HTTP):** Connects to `http://localhost:8051/sse`.
    -   **IDE (Stdio):** Starts `archon-mcp` process via `docker exec` or `uv run`.
2.  **Interception:**
    -   **HTTP:** A Middleware on the MCP server intercepts the `/sse` endpoint to register/unregister sessions.
    -   **Stdio:** The server entry point registers a session on startup and unregisters on exit.
3.  **State Management:**
    -   `McpSessionManager` (Singleton) stores active sessions in memory.
4.  **Data Retrieval:**
    -   **Frontend** polls `archon-server` (`GET /api/mcp/sessions`).
    -   **Archon-Server** proxies the request to `archon-mcp` (`GET http://archon-mcp:8051/sessions`).
    -   **Archon-MCP** returns the session list from `McpSessionManager`.

### 2.2 Component Interaction
```mermaid
graph TD
    Client_HTTP[IDE (HTTP)] -->|SSE Connection| MCP_Server[Archon MCP Server :8051]
    Client_Stdio[IDE (Stdio)] -->|Process Start| MCP_Server
    
    subgraph "Archon MCP Server"
        Middleware[Connection Middleware]
        SessionMgr[Session Manager]
        API_Endpoint[GET /sessions]
    end
    
    Middleware -->|Register/Unregister| SessionMgr
    API_Endpoint -->|Read| SessionMgr
    
    Frontend[Archon Dashboard] -->|Polls| Backend_API[Archon Backend :8181]
    Backend_API -->|Proxies| API_Endpoint
```

## 3. Data Structures

### 3.1 Session Model
We will upgrade the existing `SimplifiedSessionManager` to store rich objects.

```python
@dataclass
class McpSession:
    session_id: str
    transport: str  # "sse" | "stdio"
    created_at: datetime
    last_active: datetime
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
```

### 3.2 API Response Format (`GET /sessions`)
```json
{
  "success": true,
  "timestamp": "2023-10-27T10:00:00Z",
  "summary": {
    "total_active": 2,
    "by_transport": {
      "sse": 1,
      "stdio": 1
    }
  },
  "sessions": [
    {
      "session_id": "uuid-1",
      "transport": "sse",
      "uptime_seconds": 120,
      "client_ip": "127.0.0.1"
    },
    {
      "session_id": "uuid-2",
      "transport": "stdio",
      "uptime_seconds": 300
    }
  ]
}
```

## 4. Backend Implementation Plan

### 4.1 Enhance `McpSessionManager`
**File:** `python/src/server/services/mcp_session_manager.py`
-   **Action:** Refactor `SimplifiedSessionManager` to use the `McpSession` dataclass.
-   **New Methods:**
    -   `register_session(transport, ip=None, ua=None) -> session_id`
    -   `unregister_session(session_id)`
    -   `get_all_sessions() -> List[McpSession]`

### 4.2 Implement Connection Tracking (Archon MCP)
**File:** `python/src/mcp_server/mcp_server.py`

#### A. Stdio Tracking
-   **Logic:** In the `main()` function, before `mcp.run(transport="stdio")`:
    1.  Call `session_manager.register_session("stdio")`.
    2.  Use a `try...finally` block to ensure `unregister_session` is called when the process exits.

#### B. HTTP (SSE) Tracking
-   **Logic:** Since `FastMCP` wraps the ASGI app, we need to inject a middleware.
-   **Implementation:**
    1.  Define a `SessionMiddleware` class (inheriting from `BaseHTTPMiddleware` or pure ASGI).
    2.  Intercept requests to `/sse`.
    3.  On connect: `register_session("sse")`.
    4.  On disconnect: `unregister_session()`.
    5.  *Note:* If `FastMCP` does not expose the app directly, we may need to use `mcp.fastapi_app.add_middleware(...)` if available, or wrap the application execution.

### 4.3 Expose Session Endpoint
**File:** `python/src/mcp_server/mcp_server.py`
-   **Action:** Add a new custom route using `FastMCP`.
    ```python
    @mcp.custom_route("/sessions", methods=["GET"])
    async def get_sessions_endpoint(request):
        # ... fetch from manager and return JSON ...
    ```

### 4.4 Update Archon Backend Proxy
**File:** `python/src/server/api_routes/mcp_api.py`
-   **Action:** Update `get_mcp_sessions` to fetch data from `http://localhost:8051/sessions` (using `get_mcp_url()`) instead of returning placeholder data.

## 5. Frontend Implementation Plan

### 5.1 Create `SessionBlock` Component
**File:** `archon-ui-main/src/features/mcp/components/SessionBlock.tsx`
-   **UI Design:**
    -   Card layout matching existing dashboard style.
    -   **Header:** "Active Sessions" with a badge count.
    -   **List:** Scrollable list of sessions.
    -   **Items:** Icon (Globe for HTTP, Terminal for Stdio), Session ID (truncated), Duration (e.g., "5m 30s").
    -   **Empty State:** "No active clients connected."

### 5.2 Integrate into Dashboard
**File:** `archon-ui-main/src/features/mcp/pages/McpDashboard.tsx`
-   **Action:** Add `<SessionBlock />` to the grid layout, likely near the Status Bar or Server Config section.

### 5.3 Data Fetching
-   **Hook:** Use `useQuery` (TanStack Query) to poll `/api/mcp/sessions` every 5-10 seconds.

## 6. Step-by-Step Execution Guide

1.  **Backend (Session Manager):** Modify `mcp_session_manager.py` to support rich session data.
2.  **Backend (MCP Server):**
    -   Add `register_session` call for Stdio mode in `mcp_server.py`.
    -   Implement Middleware for SSE mode in `mcp_server.py`.
    -   Add `/sessions` endpoint in `mcp_server.py`.
3.  **Backend (API Proxy):** Update `mcp_api.py` to proxy the request.
4.  **Frontend:** Create component and integrate.
5.  **Testing:**
    -   Start server in Docker.
    -   Connect via Browser (HTTP) -> Verify session shows up.
    -   Connect via `claude mcp` (Stdio) -> Verify session shows up.

## 7. Risks & Mitigations
-   **Risk:** `FastMCP` might not easily allow middleware injection for the `/sse` route.
    -   **Mitigation:** If middleware fails, fallback to "Activity-Based" tracking (update timestamp on every tool call) and expire sessions after short timeout (e.g., 1 min).
-   **Risk:** Stdio process termination might not always trigger cleanup (e.g., `kill -9`).
    -   **Mitigation:** Accept that Stdio sessions might persist until server restart in rare crash cases, or implement a heartbeat if possible (harder with Stdio).
