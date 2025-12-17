import { Clock, Globe, Monitor, Terminal } from "lucide-react";
import type React from "react";
import type { McpSession } from "../types";

interface SessionBlockProps {
  sessions: McpSession[];
}

export const SessionBlock: React.FC<SessionBlockProps> = ({ sessions }) => {
  const formatDuration = (seconds?: number) => {
    if (!seconds) return "0s";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  const getClientInfo = (session: McpSession) => {
    // Priority 1: Use explicit client name from MCP handshake (if available)
    if (session.client_name) {
      const name = session.client_name;
      const lowerName = name.toLowerCase();
      
      if (lowerName.includes("cline")) return { name: "Cline", icon: <Terminal className="w-4 h-4 text-purple-500" /> };
      if (lowerName.includes("cursor")) return { name: "Cursor", icon: <Terminal className="w-4 h-4 text-blue-500" /> };
      if (lowerName.includes("windsurf")) return { name: "Windsurf", icon: <Terminal className="w-4 h-4 text-teal-500" /> };
      if (lowerName.includes("vscode")) return { name: "VS Code", icon: <Terminal className="w-4 h-4 text-blue-600" /> };
      if (lowerName.includes("claude")) return { name: "Claude", icon: <Globe className="w-4 h-4 text-orange-500" /> };
      
      return { name: name, icon: <Terminal className="w-4 h-4 text-indigo-500" /> };
    }

    // Priority 2: Fallback to User Agent parsing
    const ua = session.user_agent || "";
    const lowerUa = ua.toLowerCase();
    
    if (lowerUa.includes("cline")) return { name: "Cline", icon: <Terminal className="w-4 h-4 text-purple-500" /> };
    if (lowerUa.includes("cursor")) return { name: "Cursor", icon: <Terminal className="w-4 h-4 text-blue-500" /> };
    if (lowerUa.includes("windsurf")) return { name: "Windsurf", icon: <Terminal className="w-4 h-4 text-teal-500" /> };
    if (lowerUa.includes("vscode")) return { name: "VS Code", icon: <Terminal className="w-4 h-4 text-blue-600" /> };
    if (lowerUa.includes("claude")) return { name: "Claude", icon: <Globe className="w-4 h-4 text-orange-500" /> };
    if (lowerUa.includes("kilo")) return { name: "Kilo Code", icon: <Terminal className="w-4 h-4 text-indigo-500" /> };
    if (lowerUa.includes("stdio-client")) return { name: "Stdio Process", icon: <Terminal className="w-4 h-4 text-gray-500" /> };
    
    // Improved fallback: handle leading slashes or empty parts
    const parts = ua.split('/');
    const name = parts.find(p => p.trim().length > 0) || "Unknown Client";
    return { name, icon: null };
  };

  const getTransportLabel = (session: McpSession) => {
    if (session.transport === "stdio") return "STDIO";
    if (session.transport === "sse") return "SSE";
    return session.transport.toUpperCase();
  };

  const getIcon = (session: McpSession) => {
    const clientInfo = getClientInfo(session);
    if (clientInfo.icon) return clientInfo.icon;
    
    if (session.transport === "stdio") return <Terminal className="w-4 h-4 text-purple-500" />;
    if (session.transport === "sse") return <Globe className="w-4 h-4 text-green-500" />;
    return <Monitor className="w-4 h-4 text-gray-500" />;
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
      {sessions.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
          No active clients connected.
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => {
            const clientInfo = getClientInfo(session);
            const transportLabel = getTransportLabel(session);
            
            return (
              <div 
                key={session.session_id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-100 dark:border-gray-700"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white dark:bg-gray-800 rounded-md shadow-sm">
                    {getIcon(session)}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-200 flex items-center gap-2">
                      <span className="uppercase text-xs font-bold text-gray-400">{transportLabel}</span>
                      <span className="text-gray-300 dark:text-gray-600">•</span>
                      <span>{clientInfo.name}</span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 flex items-center gap-2">
                      <span className="font-mono opacity-70" title={session.session_id}>
                        {session.session_id.substring(0, 8)}...
                      </span>
                      <span>•</span>
                      <span>{session.client_ip || "Local Process"}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 px-2 py-1 rounded border border-gray-100 dark:border-gray-600">
                  <Clock className="w-3 h-3" />
                  {formatDuration(session.uptime_seconds)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
