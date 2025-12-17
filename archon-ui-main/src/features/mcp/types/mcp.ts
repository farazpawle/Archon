// Core MCP interfaces matching backend schema
export interface McpServerStatus {
  status: "running" | "starting" | "stopped" | "stopping";
  uptime: number | null;
  logs: string[];
}

export interface McpServerConfig {
  transport: string;
  host: string;
  port: number;
  model?: string;
}

export interface McpClient {
  session_id: string;
  client_type: "Claude" | "Cursor" | "Windsurf" | "Cline" | "KiRo" | "Augment" | "Gemini" | "Unknown";
  connected_at: string;
  last_activity: string;
  status: "active" | "idle";
}

export interface McpSession {
  session_id: string;
  transport: string;
  created_at: string;
  last_active: string;
  client_ip?: string;
  user_agent?: string;
  client_name?: string;
  client_version?: string;
  uptime_seconds?: number;
}

export interface McpSessionInfo {
  active_sessions: number;
  session_timeout: number;
  server_uptime_seconds?: number;
  sessions?: McpSession[];
  clients?: McpClient[];
}

// we actually support all ides and mcp clients
export type SupportedIDE =
  | "windsurf"
  | "cursor"
  | "claudecode"
  | "cline"
  | "kiro"
  | "codex"
  | "gemini"
  | "githubcopilot";

export interface IdeConfiguration {
  ide: SupportedIDE;
  title: string;
  steps: string[];
  config: string;
  supportsOneClick?: boolean;
}
