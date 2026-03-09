from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionState:
    transcript: str = ""
    notifications: list[str] = field(default_factory=list)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState()
        return self._sessions[session_id]

    def reset(self, session_id: str | None = None) -> None:
        if session_id:
            self._sessions[session_id] = SessionState()
            return
        self._sessions = {}

