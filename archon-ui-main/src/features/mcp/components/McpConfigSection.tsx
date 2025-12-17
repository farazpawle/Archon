import { Copy, ExternalLink, Terminal, Globe, Box, Laptop } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { useToast } from "@/features/shared/hooks";
import { copyToClipboard } from "../../shared/utils/clipboard";
import { Button, cn, glassmorphism, Tabs, TabsContent, TabsList, TabsTrigger, ToggleGroup, ToggleGroupItem } from "../../ui/primitives";
import type { McpServerConfig, McpServerStatus, SupportedIDE } from "../types";

interface McpConfigSectionProps {
  config?: McpServerConfig;
  status: McpServerStatus;
  className?: string;
}

type TransportMode = "http" | "stdio";
type DeploymentMode = "docker" | "native";

interface ConfigOptions {
  transport: TransportMode;
  deployment: DeploymentMode;
}

const ideConfigurations: Record<
  SupportedIDE,
  {
    title: string;
    steps: (options: ConfigOptions) => string[];
    configGenerator: (config: McpServerConfig, options: ConfigOptions) => string;
    supportsOneClick?: boolean;
    platformSpecific?: boolean;
    supportsStdio: boolean;
  }
> = {
  claudecode: {
    title: "Claude Code Configuration",
    supportsStdio: true,
    steps: () => [
      "Open a terminal and run the following command:",
      "The connection will be established automatically",
    ],
    configGenerator: (config, options) => {
      if (options.transport === "http") {
        return JSON.stringify(
          {
            name: "archon",
            transport: "http",
            url: `http://${config.host}:${config.port}/sse`,
          },
          null,
          2,
        );
      }
      // Stdio
      const args = options.deployment === "docker"
        ? ["exec", "-i", "-e", "TRANSPORT=stdio", "archon-mcp", "python", "-m", "src.mcp_server.mcp_server"]
        : ["run", "python", "-m", "src.mcp_server.mcp_server"];
      
      const command = options.deployment === "docker" ? "docker" : "uv";

      return JSON.stringify(
        {
          name: "archon",
          transport: "stdio",
          command: command,
          args: args,
          env: options.deployment === "native" ? { TRANSPORT: "stdio" } : undefined
        },
        null,
        2,
      );
    },
  },
  githubcopilot: {
    title: "GitHub Copilot Configuration",
    supportsStdio: true,
    steps: (options) => [
      "Open VS Code settings (Cmd/Ctrl + ,)",
      'Search for "github.copilot.mcpServers"',
      'Click "Edit in settings.json"',
      "Add the configuration shown below",
      "Restart VS Code for changes to take effect",
    ],
    configGenerator: (config, options) => {
      if (options.transport === "http") {
        return JSON.stringify(
          {
            "github.copilot.mcpServers": {
              "archon-sse": {
                type: "sse",
                url: `http://${config.host}:${config.port}/sse`,
              },
            },
          },
          null,
          2,
        );
      }
      // Stdio
      const args = options.deployment === "docker"
        ? ["exec", "-i", "-e", "TRANSPORT=stdio", "archon-mcp", "python", "-m", "src.mcp_server.mcp_server"]
        : ["run", "python", "-m", "src.mcp_server.mcp_server"];
      
      const command = options.deployment === "docker" ? "docker" : "uv";

      return JSON.stringify(
        {
          "github.copilot.mcpServers": {
            "archon-stdio": {
              type: "stdio",
              command: command,
              args: args,
              env: options.deployment === "native" ? { TRANSPORT: "stdio" } : undefined
            },
          },
        },
        null,
        2,
      );
    },
  },
  gemini: {
    title: "Gemini CLI Configuration",
    supportsStdio: true,
    steps: (options) => [
      "Locate or create the settings file at ~/.gemini/settings.json",
      "Add the configuration shown below to the file",
      "Launch Gemini CLI in your terminal",
      "Test the connection by typing /mcp to list available tools",
    ],
    configGenerator: (config, options) => {
      if (options.transport === "http") {
        return JSON.stringify(
          {
            mcpServers: {
              archon: {
                httpUrl: `http://${config.host}:${config.port}/sse`,
              },
            },
          },
          null,
          2,
        );
      }
      // Stdio
      const args = options.deployment === "docker"
        ? ["exec", "-i", "-e", "TRANSPORT=stdio", "archon-mcp", "python", "-m", "src.mcp_server.mcp_server"]
        : ["run", "python", "-m", "src.mcp_server.mcp_server"];
      
      const command = options.deployment === "docker" ? "docker" : "uv";

      return JSON.stringify(
        {
          mcpServers: {
            archon: {
              command: command,
              args: args,
              env: options.deployment === "native" ? { TRANSPORT: "stdio" } : undefined
            },
          },
        },
        null,
        2,
      );
    },
  },
  codex: {
    title: "Codex Configuration",
    supportsStdio: false,
    steps: (options) => [
      "Step 1: Install mcp-remote globally: npm install -g mcp-remote",
      "Step 2: Add configuration to ~/.codex/config.toml",
      "Step 3: Find your exact mcp-remote path by running: npm root -g",
      "Step 4: Replace the path in the configuration with your actual path + /mcp-remote/dist/proxy.js",
    ],
    configGenerator: (config, options) => {
      const isWindows = navigator.platform.toLowerCase().includes("win");

      if (isWindows) {
        return `[mcp_servers.archon]
command = 'node'
args = [
    'C:/Users/YOUR_USERNAME/AppData/Roaming/npm/node_modules/mcp-remote/dist/proxy.js',
    'http://${config.host}:${config.port}/sse'
]
env = {
    APPDATA = 'C:\\Users\\YOUR_USERNAME\\AppData\\Roaming',
    LOCALAPPDATA = 'C:\\Users\\YOUR_USERNAME\\AppData\\Local',
    SystemRoot = 'C:\\WINDOWS',
    COMSPEC = 'C:\\WINDOWS\\system32\\cmd.exe'
}`;
      } else {
        return `[mcp_servers.archon]
command = 'node'
args = [
    '/usr/local/lib/node_modules/mcp-remote/dist/proxy.js',
    'http://${config.host}:${config.port}/sse'
]
env = { }`;
      }
    },
    platformSpecific: true,
  },
  cursor: {
    title: "Cursor Configuration",
    supportsStdio: true,
    steps: (options) => [
      "Option A: Use the one-click install button below (recommended for HTTP)",
      "Option B: Manually edit ~/.cursor/mcp.json",
      "Add the configuration shown below",
      "Restart Cursor for changes to take effect",
    ],
    configGenerator: (config, options) => {
      if (options.transport === "http") {
        return JSON.stringify(
          {
            mcpServers: {
              archon: {
                url: `http://${config.host}:${config.port}/sse`,
              },
            },
          },
          null,
          2,
        );
      }
      // Stdio
      const args = options.deployment === "docker"
        ? ["exec", "-i", "-e", "TRANSPORT=stdio", "archon-mcp", "python", "-m", "src.mcp_server.mcp_server"]
        : ["run", "python", "-m", "src.mcp_server.mcp_server"];
      
      const command = options.deployment === "docker" ? "docker" : "uv";

      return JSON.stringify(
        {
          mcpServers: {
            archon: {
              command: command,
              args: args,
              env: options.deployment === "native" ? { TRANSPORT: "stdio" } : undefined
            },
          },
        },
        null,
        2,
      );
    },
    supportsOneClick: true,
  },
  windsurf: {
    title: "Windsurf Configuration",
    supportsStdio: true,
    steps: (options) => [
      'Open Windsurf and click the "MCP servers" button (hammer icon)',
      'Click "Configure" and then "View raw config"',
      "Add the configuration shown below to the mcpServers object",
      'Click "Refresh" to connect to the server',
    ],
    configGenerator: (config, options) => {
      if (options.transport === "http") {
        return JSON.stringify(
          {
            mcpServers: {
              archon: {
                serverUrl: `http://${config.host}:${config.port}/sse`,
              },
            },
          },
          null,
          2,
        );
      }
      // Stdio
      const args = options.deployment === "docker"
        ? ["exec", "-i", "-e", "TRANSPORT=stdio", "archon-mcp", "python", "-m", "src.mcp_server.mcp_server"]
        : ["run", "python", "-m", "src.mcp_server.mcp_server"];
      
      const command = options.deployment === "docker" ? "docker" : "uv";

      return JSON.stringify(
        {
          mcpServers: {
            archon: {
              command: command,
              args: args,
              env: options.deployment === "native" ? { TRANSPORT: "stdio" } : undefined
            },
          },
        },
        null,
        2,
      );
    },
  },
  cline: {
    title: "Cline Configuration",
    supportsStdio: true,
    steps: (options) => [
      "Open VS Code settings (Cmd/Ctrl + ,)",
      'Search for "cline.mcpServers"',
      'Click "Edit in settings.json"',
      "Add the configuration shown below",
      "Restart VS Code for changes to take effect",
    ],
    configGenerator: (config, options) => {
      if (options.transport === "http") {
        return JSON.stringify(
          {
            mcpServers: {
              archon: {
                command: "npx",
                args: ["mcp-remote", `http://${config.host}:${config.port}/sse`, "--allow-http"],
              },
            },
          },
          null,
          2,
        );
      }
      // Stdio
      const args = options.deployment === "docker"
        ? ["exec", "-i", "-e", "TRANSPORT=stdio", "archon-mcp", "python", "-m", "src.mcp_server.mcp_server"]
        : ["run", "python", "-m", "src.mcp_server.mcp_server"];
      
      const command = options.deployment === "docker" ? "docker" : "uv";

      return JSON.stringify(
        {
          mcpServers: {
            archon: {
              command: command,
              args: args,
              env: options.deployment === "native" ? { TRANSPORT: "stdio" } : undefined
            },
          },
        },
        null,
        2,
      );
    },
  },
  kiro: {
    title: "Kiro Configuration",
    supportsStdio: true,
    steps: (options) => [
      "Open Kiro settings",
      "Navigate to MCP Servers section",
      "Add the configuration shown below",
      "Save and restart Kiro",
    ],
    configGenerator: (config, options) => {
      if (options.transport === "http") {
        return JSON.stringify(
          {
            mcpServers: {
              archon: {
                command: "npx",
                args: ["mcp-remote", `http://${config.host}:${config.port}/sse`, "--allow-http"],
              },
            },
          },
          null,
          2,
        );
      }
      // Stdio
      const args = options.deployment === "docker"
        ? ["exec", "-i", "-e", "TRANSPORT=stdio", "archon-mcp", "python", "-m", "src.mcp_server.mcp_server"]
        : ["run", "python", "-m", "src.mcp_server.mcp_server"];
      
      const command = options.deployment === "docker" ? "docker" : "uv";

      return JSON.stringify(
        {
          mcpServers: {
            archon: {
              command: command,
              args: args,
              env: options.deployment === "native" ? { TRANSPORT: "stdio" } : undefined
            },
          },
        },
        null,
        2,
      );
    },
  },
};

export const McpConfigSection: React.FC<McpConfigSectionProps> = ({ config, status, className }) => {
  const [selectedIDE, setSelectedIDE] = useState<SupportedIDE>("claudecode");
  const [transportMode, setTransportMode] = useState<TransportMode>("http");
  const [deploymentMode, setDeploymentMode] = useState<DeploymentMode>("docker");
  const { showToast } = useToast();

  if (status.status !== "running" || !config) {
    return (
      <div
        className={cn(
          "p-6 text-center rounded-lg",
          glassmorphism.background.subtle,
          glassmorphism.border.default,
          className,
        )}
      >
        <p className="text-zinc-400">Start the MCP server to see configuration options</p>
      </div>
    );
  }

  const selectedConfig = ideConfigurations[selectedIDE];
  const supportsStdio = selectedConfig.supportsStdio;

  const handleCopyConfig = async () => {
    if (transportMode === "stdio" && !supportsStdio) {
        showToast("This agent doesn't support stdio", "error");
        return;
    }
    const configText = selectedConfig.configGenerator(config, { transport: transportMode, deployment: deploymentMode });
    const result = await copyToClipboard(configText);

    if (result.success) {
      showToast("Configuration copied to clipboard", "success");
    } else {
      console.error("Failed to copy config:", result.error);
      showToast("Failed to copy configuration", "error");
    }
  };

  const handleCursorOneClick = () => {
    const httpConfig = {
      url: `http://${config.host}:${config.port}/mcp`,
    };
    const configString = JSON.stringify(httpConfig);
    const base64Config = btoa(configString);
    const deeplink = `cursor://anysphere.cursor-deeplink/mcp/install?name=archon&config=${base64Config}`;
    window.location.href = deeplink;
    showToast("Opening Cursor with Archon MCP configuration...", "info");
  };

  const handleClaudeCodeCommand = async () => {
    let command = "";
    if (transportMode === "http") {
      command = `claude mcp add --transport http archon http://${config.host}:${config.port}/sse`;
    } else {
      if (deploymentMode === "docker") {
        command = `claude mcp add archon -- docker exec -i -e TRANSPORT=stdio archon-mcp python -m src.mcp_server.mcp_server`;
      } else {
        command = `claude mcp add archon -- uv run python -m src.mcp_server.mcp_server`;
      }
    }
    
    const result = await copyToClipboard(command);

    if (result.success) {
      showToast("Command copied to clipboard", "success");
    } else {
      console.error("Failed to copy command:", result.error);
      showToast("Failed to copy command", "error");
    }
  };

  const configText = selectedConfig.configGenerator(config, { transport: transportMode, deployment: deploymentMode });

  return (
    <div className={cn("space-y-6", className)}>
      {/* Universal MCP Note */}
      <div className={cn("p-3 rounded-lg", glassmorphism.background.blue, glassmorphism.border.blue)}>
        <p className="text-sm text-blue-700 dark:text-blue-300">
          <span className="font-semibold">Note:</span> Archon works with any application that supports MCP. Below are
          instructions for common tools, but these steps can be adapted for any MCP-compatible client.
        </p>
      </div>

      {/* IDE Selection Tabs */}
      <Tabs
        defaultValue="claudecode"
        value={selectedIDE}
        onValueChange={(value) => setSelectedIDE(value as SupportedIDE)}
      >
        <TabsList className="grid grid-cols-4 lg:grid-cols-8 w-full">
          <TabsTrigger value="claudecode">Claude Code</TabsTrigger>
          <TabsTrigger value="githubcopilot">GitHub Copilot</TabsTrigger>
          <TabsTrigger value="cursor">Cursor</TabsTrigger>
          <TabsTrigger value="windsurf">Windsurf</TabsTrigger>
          <TabsTrigger value="cline">Cline</TabsTrigger>
          <TabsTrigger value="kiro">Kiro</TabsTrigger>
          <TabsTrigger value="gemini">Gemini</TabsTrigger>
          <TabsTrigger value="codex">Codex</TabsTrigger>
        </TabsList>

        <TabsContent value={selectedIDE} className="mt-6 space-y-4">
          {/* Configuration Controls */}
          <div
            className={cn(
              "relative flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center p-4 rounded-lg",
              glassmorphism.background.card,
              glassmorphism.border.default,
              glassmorphism.shadow.elevated,
              glassmorphism.border.hover,
            )}
          >
            <div className="space-y-1">
              <h5 className="text-sm font-medium text-gray-700 dark:text-zinc-300">Connection Type</h5>
              <p className="text-xs text-gray-500 dark:text-zinc-500">Choose how the IDE connects to Archon</p>
            </div>
            <div className="flex">
              <ToggleGroup
                type="single"
                value={transportMode}
                onValueChange={(v) => v && setTransportMode(v as TransportMode)}
                className="p-1 gap-1"
              >
                <ToggleGroupItem value="http" aria-label="HTTP Transport" size="md" className="rounded-md">
                  <Globe className="w-4 h-4 mr-2" />
                  HTTP (SSE)
                </ToggleGroupItem>
                <ToggleGroupItem
                  value="stdio"
                  aria-label="Stdio Transport"
                  size="md"
                  disabled={!supportsStdio}
                  className={cn("rounded-md", glassmorphism.interactive.disabled)}
                >
                  <Terminal className="w-4 h-4 mr-2" />
                  Stdio
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
          </div>

          {transportMode === "stdio" && supportsStdio && (
            <div
              className={cn(
                "relative flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center p-4 rounded-lg",
                glassmorphism.background.card,
                glassmorphism.border.default,
                glassmorphism.shadow.elevated,
                glassmorphism.border.hover,
              )}
            >
              <div className="space-y-1">
                <h5 className="text-sm font-medium text-gray-700 dark:text-zinc-300">Deployment Mode</h5>
                <p className="text-xs text-gray-500 dark:text-zinc-500">How Archon is running locally</p>
              </div>
              <div className="flex">
                <ToggleGroup
                  type="single"
                  value={deploymentMode}
                  onValueChange={(v) => v && setDeploymentMode(v as DeploymentMode)}
                  className="p-1 gap-1"
                >
                  <ToggleGroupItem value="docker" aria-label="Docker Deployment" size="md" className="rounded-md">
                    <Box className="w-4 h-4 mr-2" />
                    Docker
                  </ToggleGroupItem>
                  <ToggleGroupItem value="native" aria-label="Native Deployment" size="md" className="rounded-md">
                    <Laptop className="w-4 h-4 mr-2" />
                    Native
                  </ToggleGroupItem>
                </ToggleGroup>
              </div>
            </div>
          )}

          {/* Configuration Title and Steps */}
          <div>
            <h4 className="text-lg font-semibold text-gray-800 dark:text-white mb-3">{selectedConfig.title}</h4>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600 dark:text-zinc-400">
              {selectedConfig.steps({ transport: transportMode, deployment: deploymentMode }).map((step) => {
                // Highlight npm install command for Codex
                if (selectedIDE === "codex" && step.includes("npm install -g mcp-remote")) {
                  const parts = step.split("npm install -g mcp-remote");
                  return (
                    <li key={step}>
                      {parts[0]}
                      <code className="font-mono font-semibold bg-zinc-800 text-cyan-400 px-1.5 py-0.5 rounded">
                        npm install -g mcp-remote
                      </code>
                      {parts[1]}
                    </li>
                  );
                }
                return <li key={step}>{step}</li>;
              })}
            </ol>
            {/* macOS note for Codex */}
            {selectedIDE === "codex" && (
              <p className="mt-2 text-sm text-gray-600 dark:text-zinc-400 italic">
                Note: On macOS with Homebrew on Apple Silicon, the path might be{" "}
                <code className="text-xs font-mono bg-zinc-800 px-1 rounded">
                  /opt/homebrew/lib/node_modules/mcp-remote/dist/proxy.js
                </code>
              </p>
            )}
          </div>

          {/* Special Commands for Claude Code */}
          {selectedIDE === "claudecode" && (
            <div
              className={cn(
                "p-3 rounded-lg flex items-center justify-between",
                glassmorphism.background.subtle,
                glassmorphism.border.default,
              )}
            >
              <code className="text-sm font-mono text-cyan-600 dark:text-cyan-400 break-all">
                {transportMode === "http" 
                  ? `claude mcp add --transport http archon http://${config.host}:${config.port}/sse`
                  : deploymentMode === "docker"
                    ? `claude mcp add archon -- docker exec -i -e TRANSPORT=stdio archon-mcp python -m src.mcp_server.mcp_server`
                    : `claude mcp add archon -- uv run python -m src.mcp_server.mcp_server`
                }
              </code>
              <Button variant="outline" size="sm" onClick={handleClaudeCodeCommand} className="shrink-0 ml-2">
                <Copy className="w-3 h-3 mr-1" />
                Copy
              </Button>
            </div>
          )}

          {/* Platform-specific note for Codex */}
          {selectedIDE === "codex" && (
            <div className={cn("p-3 rounded-lg", glassmorphism.background.card, glassmorphism.border.default)}>
              <p className="text-sm text-yellow-700 dark:text-yellow-300">
                <span className="font-semibold">Platform Note:</span> The configuration below shows{" "}
                {navigator.platform.toLowerCase().includes("win") ? "Windows" : "Linux/macOS"} format. Adjust paths
                according to your system. This setup is complex right now because Codex has some bugs with MCP
                currently.
              </p>
            </div>
          )}

          {/* Configuration Display */}
          <div className={cn("relative rounded-lg p-4", glassmorphism.background.subtle, glassmorphism.border.default)}>
            {transportMode === "stdio" && !supportsStdio ? (
              <div className="flex items-center justify-center py-8 text-zinc-500 dark:text-zinc-400">
                <p>This agent doesn't support stdio</p>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                    Configuration
                    {selectedIDE === "codex" && (
                      <span className="ml-2 text-xs text-yellow-600 dark:text-yellow-400">
                        ({navigator.platform.toLowerCase().includes("win") ? "Windows" : "Linux/macOS"})
                      </span>
                    )}
                  </span>
                  <Button variant="outline" size="sm" onClick={handleCopyConfig}>
                    <Copy className="w-3 h-3 mr-1" />
                    Copy
                  </Button>
                </div>
                <pre className="text-xs font-mono text-gray-800 dark:text-zinc-200 overflow-x-auto">
                  <code>{configText}</code>
                </pre>
              </>
            )}
          </div>

          {/* One-Click Install for Cursor */}
          {selectedIDE === "cursor" && selectedConfig.supportsOneClick && transportMode === "http" && (
            <div className="flex items-center gap-3">
              <Button variant="cyan" onClick={handleCursorOneClick} className="shadow-lg">
                <ExternalLink className="w-4 h-4 mr-2" />
                One-Click Install for Cursor
              </Button>
              <span className="text-xs text-zinc-500">Opens Cursor with configuration</span>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};
