"""
MCP Session Manager

This module provides simplified session management for MCP server connections,
enabling clients to reconnect after server restarts.
"""

import uuid
import threading
import json
import os
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from pathlib import Path

# Removed direct logging import - using unified config
from ..config.logfire_config import get_logger

logger = get_logger(__name__)

SESSION_FILE = Path(tempfile.gettempdir()) / "mcp_sessions.json"

@dataclass
class McpSession:
    session_id: str
    transport: str  # "sse" | "stdio"
    created_at: datetime
    last_active: datetime
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    client_name: Optional[str] = None
    client_version: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert session to dictionary with ISO format dates"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["last_active"] = self.last_active.isoformat()
        
        # Calculate uptime
        now = datetime.now(timezone.utc)
        # Ensure created_at is timezone aware for calculation
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
            
        data["uptime_seconds"] = (now - created).total_seconds()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "McpSession":
        """Create session from dictionary"""
        # Parse ISO dates
        created_at = datetime.fromisoformat(data["created_at"])
        last_active = datetime.fromisoformat(data["last_active"])
        
        # Ensure timezone awareness
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
            
        return cls(
            session_id=data["session_id"],
            transport=data["transport"],
            created_at=created_at,
            last_active=last_active,
            client_ip=data.get("client_ip"),
            user_agent=data.get("user_agent"),
            client_name=data.get("client_name"),
            client_version=data.get("client_version")
        )


class SimplifiedSessionManager:
    """Simplified MCP session manager that tracks session IDs and expiration with file persistence"""

    def __init__(self, timeout: int = 3600):
        """
        Initialize session manager

        Args:
            timeout: Session expiration time in seconds (default: 1 hour)
        """
        self.sessions: Dict[str, McpSession] = {}  # session_id -> McpSession
        self.timeout = timeout
        self._lock = threading.RLock()
        self._load_sessions()

    def _load_sessions(self):
        """Load sessions from shared file"""
        if not SESSION_FILE.exists():
            return

        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                
            with self._lock:
                self.sessions = {}
                for session_data in data:
                    try:
                        session = McpSession.from_dict(session_data)
                        self.sessions[session.session_id] = session
                    except Exception as e:
                        logger.warning(f"Failed to parse session data: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to load sessions from file: {e}")

    def _save_sessions(self):
        """Save sessions to shared file"""
        try:
            # Convert all sessions to dicts
            with self._lock:
                sessions_list = [s.to_dict() for s in self.sessions.values()]
            
            # Atomic write: write to temp file then rename
            temp_file = SESSION_FILE.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(sessions_list, f)
            
            os.replace(temp_file, SESSION_FILE)
            
        except Exception as e:
            logger.error(f"Failed to save sessions to file: {e}")

    def register_session(self, transport: str, client_ip: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Register a new session and return its ID"""
        # Reload first to get latest state from other processes
        self._load_sessions()
        
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        session = McpSession(
            session_id=session_id,
            transport=transport,
            created_at=now,
            last_active=now,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        with self._lock:
            self.sessions[session_id] = session
            
        self._save_sessions()
        logger.info(f"Registered new {transport} session: {session_id}")
        return session_id

    def update_session_info(self, session_id: str, client_name: Optional[str] = None, client_version: Optional[str] = None) -> bool:
        """Update session with client info from MCP handshake"""
        self._load_sessions()
        
        with self._lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            updated = False
            
            if client_name:
                session.client_name = client_name
                updated = True
                
            if client_version:
                session.client_version = client_version
                updated = True
                
            if updated:
                self._save_sessions()
                logger.info(f"Updated session {session_id} with client info: {client_name} {client_version}")
                return True
                
        return False

    def unregister_session(self, session_id: str) -> bool:
        """Unregister a session by ID"""
        # Reload first to ensure we have the session
        self._load_sessions()
        
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self._save_sessions()
                logger.info(f"Unregistered session: {session_id}")
                return True
        return False

    def get_all_sessions(self) -> List[dict]:
        """Get all active sessions as dictionaries"""
        # Always reload to see sessions from other processes (like stdio)
        self._load_sessions()
        self.cleanup_expired_sessions()
        
        with self._lock:
            return [session.to_dict() for session in self.sessions.values()]

    # Legacy method for compatibility
    def create_session(self) -> str:
        """Create a new session and return its ID (Legacy wrapper)"""
        return self.register_session("sse")

    def validate_session(self, session_id: str) -> bool:
        """Validate a session ID and update last seen time"""
        self._load_sessions()
        
        with self._lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]
            now = datetime.now(timezone.utc)
            
            # Ensure last_active is timezone aware
            last_active = session.last_active
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)

            if now - last_active > timedelta(seconds=self.timeout):
                # Session expired, remove it
                del self.sessions[session_id]
                self._save_sessions()
                logger.info(f"Session {session_id} expired and removed")
                return False

            # Update last seen time
            session.last_active = now
            self._save_sessions()
            return True

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions"""
        # Note: We don't reload here to avoid recursion loops if called from get_all_sessions
        # But we should probably reload if called externally. 
        # For safety, let's rely on the caller (get_all_sessions) to reload first.
        
        now = datetime.now(timezone.utc)
        expired = []

        with self._lock:
            for session_id, session in self.sessions.items():
                # Ensure last_active is timezone aware
                last_active = session.last_active
                if last_active.tzinfo is None:
                    last_active = last_active.replace(tzinfo=timezone.utc)
                    
                if now - last_active > timedelta(seconds=self.timeout):
                    expired.append(session_id)

            if expired:
                for session_id in expired:
                    del self.sessions[session_id]
                self._save_sessions()
                logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)

    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        self._load_sessions()
        # Clean up expired sessions first
        self.cleanup_expired_sessions()
        with self._lock:
            return len(self.sessions)


# Global session manager instance
_session_manager: SimplifiedSessionManager | None = None


def get_session_manager() -> SimplifiedSessionManager:
    """Get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SimplifiedSessionManager()
    return _session_manager
