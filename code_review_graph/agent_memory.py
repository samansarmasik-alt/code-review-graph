"""Bounded local shared memory for concurrent ForceGraph agents."""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

_ALLOWED_KINDS = {"note", "decision", "finding", "handoff"}
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|token|password|passwd|secret)"
    r"(\s*[:=]\s*)([\"']?)([^\s,;\"']{4,})"
)
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/-]{8,}=*")


def resolve_agent_id(explicit: str | None = None) -> str:
    """Resolve a local agent identity without user configuration."""
    candidate = (explicit or "").strip()
    if candidate and candidate.lower() not in {"auto", "agent"}:
        if len(candidate) > 80:
            raise ValueError("agent_id must be at most 80 characters")
        return candidate
    for variable in (
        "FORCEGRAPH_AGENT_ID",
        "CODEX_THREAD_ID",
        "CLAUDE_SESSION_ID",
        "AGENT_ID",
    ):
        value = os.environ.get(variable, "").strip()
        if value:
            return value[:80]
    return f"agent-{os.getpid()}"


def resolve_task_id(repo_root: Path, explicit: str | None = None) -> str:
    """Resolve task identity from explicit input, env, git branch, or workspace."""
    candidate = (explicit or "").strip()
    if not candidate:
        candidate = os.environ.get("FORCEGRAPH_TASK_ID", "").strip()
    if candidate:
        if len(candidate) > 120:
            raise ValueError("task_id must be at most 120 characters")
        return candidate
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root.expanduser().resolve()), "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=2,
        )
        branch = completed.stdout.strip()
        if completed.returncode == 0 and branch:
            return f"branch:{branch}"[:120]
    except (OSError, subprocess.SubprocessError):
        pass
    return "workspace"


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
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS task_passports (
            task_id TEXT PRIMARY KEY,
            goal TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            owner_agent TEXT,
            summary TEXT,
            next_action TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
        """
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
    normalized_agent = (agent_id.strip() or f"agent-{os.getpid()}")[:80]
    normalized_task = task_id.strip()[:120] if task_id else None
    requested_kind = kind.strip().lower()
    normalized_kind = requested_kind if requested_kind in _ALLOWED_KINDS else "note"
    try:
        optimized_ttl = max(1, min(int(ttl_hours), 8760))
    except (TypeError, ValueError):
        optimized_ttl = 72
    normalized_content = _redact_memory_content(content.strip())
    if not normalized_content:
        raise ValueError("content must not be empty")

    now = time.time()
    expires_at = now + optimized_ttl * 3600
    connection = _connect(repo_root)
    try:
        with connection:
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
    finally:
        connection.close()

    return {
        "id": entry_id,
        "task_id": normalized_task,
        "agent_id": normalized_agent,
        "kind": normalized_kind,
        "created_at": now,
        "expires_at": expires_at,
        "redacted": normalized_content != content.strip(),
        "stored_chars": len(normalized_content),
        "kind_fallback": normalized_kind != requested_kind,
        "optimized_ttl_hours": optimized_ttl,
    }


def read_agent_memory(
    repo_root: Path,
    *,
    task_id: str | None = None,
    limit: int = 12,
    max_chars: int = 2400,
) -> dict[str, Any]:
    """Read recent entries using a soft, optimized model-context budget."""
    try:
        optimized_limit = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        optimized_limit = 12
    try:
        optimized_max_chars = max(200, min(int(max_chars), 100_000))
    except (TypeError, ValueError):
        optimized_max_chars = 2400

    now = time.time()
    normalized_task = task_id.strip() if task_id else None
    connection = _connect(repo_root)
    try:
        with connection:
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
                    (now, optimized_limit),
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
                    (now, normalized_task, optimized_limit),
                ).fetchall()
    finally:
        connection.close()

    selected: list[dict[str, Any]] = []
    used_chars = 0
    truncated = False
    for row in rows:
        item = dict(row)
        item_chars = len(item["content"]) + len(item["agent_id"]) + len(item["kind"]) + 48
        if selected and used_chars + item_chars > optimized_max_chars:
            truncated = True
            break
        if item_chars > optimized_max_chars:
            available = max(
                1,
                optimized_max_chars - len(item["agent_id"]) - len(item["kind"]) - 49,
            )
            item["content"] = item["content"][:available] + "…"
            item_chars = optimized_max_chars
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
        "max_chars": optimized_max_chars,
        "requested_limit": limit,
        "optimized_limit": optimized_limit,
        "local_only": True,
    }


def ensure_task_passport(
    repo_root: Path,
    *,
    task_id: str,
    goal: str,
) -> dict[str, Any]:
    """Create a task passport once without overwriting later agent decisions."""
    normalized_task = (task_id.strip() or "workspace")[:120]
    normalized_goal = _redact_memory_content(goal.strip())
    now = time.time()
    connection = _connect(repo_root)
    try:
        with connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO task_passports
                    (task_id, goal, status, created_at, updated_at)
                VALUES (?, ?, 'active', ?, ?)
                """,
                (normalized_task, normalized_goal, now, now),
            )
    finally:
        connection.close()
    return read_task_passport(repo_root, task_id=normalized_task)


def update_task_passport(
    repo_root: Path,
    *,
    task_id: str,
    agent_id: str,
    goal: str | None = None,
    status: str | None = None,
    summary: str | None = None,
    next_action: str | None = None,
    claim: bool = False,
) -> dict[str, Any]:
    """Update only supplied passport fields; unknown statuses remain allowed."""
    normalized_task = (task_id.strip() or "workspace")[:120]
    normalized_agent = (agent_id.strip() or f"agent-{os.getpid()}")[:80]
    now = time.time()

    def clean(value: str | None) -> str | None:
        if value is None:
            return None
        return _redact_memory_content(value.strip())

    normalized_status = clean(status)
    owner = normalized_agent if claim else None
    connection = _connect(repo_root)
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO task_passports
                    (task_id, goal, status, owner_agent, summary, next_action,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    goal = COALESCE(excluded.goal, task_passports.goal),
                    status = COALESCE(excluded.status, task_passports.status),
                    owner_agent = COALESCE(excluded.owner_agent, task_passports.owner_agent),
                    summary = COALESCE(excluded.summary, task_passports.summary),
                    next_action = COALESCE(excluded.next_action, task_passports.next_action),
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_task,
                    clean(goal),
                    normalized_status or "active",
                    owner,
                    clean(summary),
                    clean(next_action),
                    now,
                    now,
                ),
            )
    finally:
        connection.close()
    return read_task_passport(repo_root, task_id=normalized_task)


def read_task_passport(
    repo_root: Path,
    *,
    task_id: str,
    max_chars: int = 2400,
) -> dict[str, Any]:
    """Read one passport and optimize text fields to the requested soft budget."""
    normalized_task = (task_id.strip() or "workspace")[:120]
    try:
        optimized_max_chars = max(400, min(int(max_chars), 100_000))
    except (TypeError, ValueError):
        optimized_max_chars = 2400

    connection = _connect(repo_root)
    try:
        row = connection.execute(
            """
            SELECT task_id, goal, status, owner_agent, summary, next_action,
                   created_at, updated_at
            FROM task_passports
            WHERE task_id = ?
            """,
            (normalized_task,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return {
            "status": "missing",
            "task_id": normalized_task,
            "passport": None,
            "local_only": True,
        }

    passport = dict(row)
    remaining = optimized_max_chars
    truncated_fields: list[str] = []
    for field in ("goal", "summary", "next_action"):
        value = passport.get(field)
        if not value:
            continue
        allowance = max(80, remaining)
        if len(value) > allowance:
            passport[field] = value[: max(1, allowance - 1)] + "…"
            truncated_fields.append(field)
        remaining = max(0, remaining - len(passport[field]))

    return {
        "status": "ok",
        "task_id": normalized_task,
        "passport": passport,
        "truncated_fields": truncated_fields,
        "optimized_max_chars": optimized_max_chars,
        "local_only": True,
    }
