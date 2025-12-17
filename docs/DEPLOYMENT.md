# Archon MCP Server Deployment Guide

This guide explains how to deploy the Archon MCP server in different modes using the Hybrid Transport System.

## Transport Modes

The server supports two transport modes, controlled by the `TRANSPORT` environment variable:

1.  **`sse` (Default)**: Streamable HTTP (Server-Sent Events). Best for remote clients, web UIs, and microservice deployments.
2.  **`stdio`**: Standard Input/Output. Best for local AI agents (Claude Desktop, Cursor, VS Code) that spawn the server as a subprocess.

## Docker Deployment

### Mode 1: HTTP/SSE (Default)

Use this mode when you need to access the MCP server over HTTP (e.g., from a web browser or another service).

```bash
# Run in background, exposing port 8051
docker run -d \
  -p 8051:8051 \
  -e TRANSPORT=sse \
  --name archon-mcp \
  archon-mcp
```

**Verification:**
Visit `http://localhost:8051/sse` (or configured endpoint) to check connectivity.

### Mode 2: Stdio (Local Agents)

Use this mode when configuring Claude Desktop or other local tools.

**Prerequisite:** The Archon stack must be running (`docker compose up -d`).

**Recommended Method: `docker exec`**
This method is the simplest as it reuses the running container's environment and network connection.

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "archon": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "-e",
        "TRANSPORT=stdio",
        "archon-mcp",
        "python",
        "-m",
        "src.mcp_server.mcp_server"
      ]
    }
  }
}
```

**Alternative Method: `docker run` (Advanced)**
If you need to run a separate container instance, you must connect it to the Docker network and provide all environment variables.

```bash
docker run -i --rm \
  -e TRANSPORT=stdio \
  -e ARCHON_SERVER_PORT=8181 \
  -e ARCHON_MCP_PORT=8051 \
  -e API_SERVICE_URL=http://archon-server:8181 \
  --env-file .env \
  --network archon_app-network \
  archon-archon-mcp:latest
```

## Troubleshooting

### "Connection Closed" or "Protocol Error" in Stdio Mode
-   **Cause**: Logs or other text appearing on `stdout`.
-   **Fix**: The server automatically redirects `stdout` to `stderr` in `stdio` mode. Ensure you are NOT using `-t` in your Docker command.
-   **Check**: Run the `docker exec` command manually in a terminal. You should see NO output until you send a JSON-RPC message.

### "Error response from daemon: pull access denied"
-   **Cause**: You are trying to `docker run` an image that doesn't exist locally by the short name.
-   **Fix**: Use the full image name `archon-archon-mcp:latest` (check `docker images`) or use the `docker exec` method above.

### Server Exits Immediately
-   **Cause**: Missing `-i` flag in Docker command.
-   **Fix**: Add `-i` to keep stdin open.
