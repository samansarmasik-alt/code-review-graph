"""Bounded local shared memory for concurrent ForceGraph agents."""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Any

_ALLOWED_KINDS = {"note", "decision", "finding", "handoff"}
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|token|password|passwd|secret)"
    r"(\s*[:=]\s*)([\"']?)([^\s,;\"']{4,})"
)
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/-]{8,}=*")


def _redact_memory_content(content: str) -> str:
    """Redact common credential assignments before local persistence."""
    redacted = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        content,
    )
    return _BEARER_TOKEN.sub("Bearer [REDACTED]", redacted)


def _memory_db_path(repo_root: Path) -> Path:
    data_dir = repo_root.expanduser().resolve() / ".code-review-graph"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "agent-memory.db"


def _connect(repo_root: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(_memory_db_path(repo_root), timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            agent_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_memory_task "
        "ON agent_memory(task_id, created_at DESC)"
    )
    connection.commit()
    return connection


def publish_agent_memory(
    repo_root: Path,
    *,
    agent_id: str,
    content: str,
    task_id: str | None = None,
    kind: str = "note",
    ttl_hours: int = 72,
) -> dict[str, Any]:
    """Publish one bounded, expiring memory entry."""
    normalized_agent = agent_id.strip()
    normalized_task = task_id.strip() if task_id else None
    normalized_kind = kind.strip().lower()
    if not normalized_agent or len(normalized_agent) > 80:
        raise ValueError("agent_id must contain 1 to 80 characters")
    if normalized_task is not None and len(normalized_task) > 120:
        raise ValueError("task_id must be at most 120 characters")
    if normalized_kind not in _ALLOWED_KINDS:
        raise ValueError("kind must be note, decision, finding, or handoff")
    if not 1 <= ttl_hours <= 720:
        raise ValueError("ttl_hours must be between 1 and 720")
    normalized_content = _redact_memory_content(content.strip())
    if not normalized_content:
        raise ValueError("content must not be empty")
    if len(normalized_content) > 4000:
        raise ValueError("content must be at most 4000 characters")

    now = time.time()
    expires_at = now + ttl_hours * 3600
    with _connect(repo_root) as connection:
        connection.execute("DELETE FROM agent_memory WHERE expires_at <= ?", (now,))
        cursor = connection.execute(
            """
            INSERT INTO agent_memory
                (task_id, agent_id, kind, content, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_task,
                normalized_agent,
                normalized_kind,
                normalized_content,
                now,
                expires_at,
            ),
        )
        entry_id = int(cursor.lastrowid)

    return {
        "id": entry_id,
        "task_id": normalized_task,
        "agent_id": normalized_agent,
        "kind": normalized_kind,
        "created_at": now,
        "expires_at": expires_at,
        "redacted": normalized_content != content.strip(),
    }


def read_agent_memory(
    repo_root: Path,
    *,
    task_id: str | None = None,
    limit: int = 12,
    max_chars: int = 2400,
) -> dict[str, Any]:
    """Read recent entries with task filtering and a strict character budget."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if not 200 <= max_chars <= 8000:
        raise ValueError("max_chars must be between 200 and 8000")

    now = time.time()
    normalized_task = task_id.strip() if task_id else None
    with _connect(repo_root) as connection:
        connection.execute("DELETE FROM agent_memory WHERE expires_at <= ?", (now,))
        if normalized_task is None:
            rows = connection.execute(
                """
                SELECT id, task_id, agent_id, kind, content, created_at, expires_at
                FROM agent_memory
                WHERE expires_at > ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, task_id, agent_id, kind, content, created_at, expires_at
                FROM agent_memory
                WHERE expires_at > ? AND task_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (now, normalized_task, limit),
            ).fetchall()

    selected: list[dict[str, Any]] = []
    used_chars = 0
    truncated = False
    for row in rows:
        item = dict(row)
        item_chars = len(item["content"]) + len(item["agent_id"]) + len(item["kind"]) + 48
        if selected and used_chars + item_chars > max_chars:
            truncated = True
            break
        if item_chars > max_chars:
            available = max(1, max_chars - len(item["agent_id"]) - len(item["kind"]) - 49)
            item["content"] = item["content"][:available] + "…"
            item_chars = max_chars
            truncated = True
        selected.append(item)
        used_chars += item_chars

    selected.reverse()
    return {
        "status": "ok",
        "task_id": normalized_task,
        "entries": selected,
        "entry_count": len(selected),
        "truncated": truncated or len(rows) > len(selected),
        "used_chars": used_chars,
        "max_chars": max_chars,
        "local_only": True,
    }
