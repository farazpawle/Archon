# Archon MCP Server - IDE Configuration Guide

This guide provides configuration instructions for using the Archon MCP Server with various IDEs.

## 1. VS Code (GitHub Copilot)

VS Code with GitHub Copilot supports both `stdio` and `sse` transport modes.

### Configuration (`.vscode/settings.json` or User Settings)

```json
{
  "github.copilot.mcp.servers": {
    "archon-stdio": {
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
    },
    "archon-sse": {
      "url": "http://localhost:8051/sse",
      "transport": "sse"
    }
  }
}
```

## 2. Void IDE (Cursor/VS Code Fork)

Void IDE typically uses a JSON configuration file for MCP servers. Ensure the JSON is valid and environment variables are correctly set.

### Configuration

If you encounter "SyntaxError: An invalid or illegal string was specified", check your JSON syntax.

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

**Note:** Void IDE might not support SSE transport fully yet. Stdio is recommended.

## 3. Kilo Code (and other Stdio-based Editors)

Kilo Code and similar editors rely heavily on standard input/output streams. The Archon server has been optimized to handle stream closures gracefully.

### Configuration

Ensure you are using the `stdio` transport mode explicitly.

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
      ],
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

### Troubleshooting "I/O operation on closed file"

If you see `ValueError('I/O operation on closed file.') lost sys.stderr`, this indicates the IDE is closing the error stream before the server has fully shut down.

**Fix:**
The latest version of Archon MCP Server includes a fix for this. Ensure you have pulled the latest changes and rebuilt the container:

```bash
docker compose build archon-mcp
docker compose up -d archon-mcp
```

## 4. Troubleshooting "Request timed out" (-32001)

If you see `MCP error -32001: Request timed out`, it means the server is taking too long to start or outputting data to stdout before the JSON-RPC handshake.

**Fixes:**
1. **Rebuild the Container:** We have optimized the startup sequence. You MUST rebuild:
   ```bash
   docker compose build archon-mcp
   docker compose up -d archon-mcp
   ```

2. **Check Docker Latency:**
   Run this command to see if `docker exec` is slow:
   ```bash
   time docker exec -i archon-mcp python -c "print('test')"
   ```
   If it takes >2 seconds, your Docker setup might be the bottleneck.

3. **Manual Restart (VS Code):**
   If the server fails to start automatically in VS Code, try reloading the window (`Ctrl+R` or `Cmd+R`).

## General Troubleshooting

### 1. Check Container Status
Ensure the MCP server container is running:
```bash
docker ps | grep archon-mcp
```

### 2. Test Stdio Connection manually
You can test if the server responds to stdio by running:
```bash
docker exec -i -e TRANSPORT=stdio archon-mcp python -m src.mcp_server.mcp_server
```
(You should see no output immediately as it waits for JSON-RPC input. Press Ctrl+C to exit.)

### 3. Check Logs
Logs are written to `/tmp/mcp_server.log` inside the container or to stderr.
```bash
docker logs archon-mcp
```
