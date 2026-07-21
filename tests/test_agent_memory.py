"""Tests for concurrent local agent memory."""

from concurrent.futures import ThreadPoolExecutor

from code_review_graph.agent_memory import (
    ensure_task_passport,
    publish_agent_memory,
    read_agent_memory,
    read_task_passport,
    resolve_agent_id,
    resolve_task_id,
    update_task_passport,
)


def test_task_identity_uses_branch_without_configuration(tmp_path, monkeypatch):
    class Result:
        returncode = 0
        stdout = "feature/login\n"

    monkeypatch.delenv("FORCEGRAPH_TASK_ID", raising=False)
    monkeypatch.setattr(
        "code_review_graph.agent_memory.subprocess.run",
        lambda *args, **kwargs: Result(),
    )
    assert resolve_task_id(tmp_path) == "branch:feature/login"


def test_task_identity_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("FORCEGRAPH_TASK_ID", "env-task")
    assert resolve_task_id(tmp_path) == "env-task"
    assert resolve_task_id(tmp_path, "explicit-task") == "explicit-task"


def test_agent_identity_uses_environment_then_process(monkeypatch):
    monkeypatch.setenv("FORCEGRAPH_AGENT_ID", "reviewer")
    assert resolve_agent_id() == "reviewer"
    monkeypatch.delenv("FORCEGRAPH_AGENT_ID")
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("AGENT_ID", raising=False)
    assert resolve_agent_id().startswith("agent-")


def test_agents_share_task_scoped_memory(tmp_path):
    publish_agent_memory(
        tmp_path,
        agent_id="planner",
        task_id="issue-42",
        kind="decision",
        content="Use the repository boundary.",
    )
    visible = read_agent_memory(tmp_path, task_id="issue-42")
    hidden = read_agent_memory(tmp_path, task_id="other")
    assert visible["entries"][0]["agent_id"] == "planner"
    assert visible["entries"][0]["kind"] == "decision"
    assert hidden["entries"] == []


def test_common_secrets_are_redacted_before_storage(tmp_path):
    result = publish_agent_memory(
        tmp_path,
        agent_id="worker",
        content="API_KEY=super-secret-value Bearer abcdefghijklmnop",
    )
    memory = read_agent_memory(tmp_path)
    assert result["redacted"] is True
    assert "super-secret-value" not in memory["entries"][0]["content"]
    assert "abcdefghijklmnop" not in memory["entries"][0]["content"]
    assert memory["entries"][0]["content"].count("[REDACTED]") == 2


def test_read_is_character_bounded(tmp_path):
    for index in range(5):
        publish_agent_memory(
            tmp_path,
            agent_id=f"worker-{index}",
            content="x" * 300,
        )
    result = read_agent_memory(tmp_path, max_chars=400)
    assert result["used_chars"] <= 400
    assert result["truncated"] is True


def test_concurrent_terminal_writes_are_visible(tmp_path):
    def write(index):
        return publish_agent_memory(
            tmp_path,
            agent_id=f"agent-{index}",
            task_id="parallel",
            content=f"finding-{index}",
            kind="finding",
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(write, range(8)))

    result = read_agent_memory(tmp_path, task_id="parallel", limit=20)
    assert result["entry_count"] == 8
    assert {entry["content"] for entry in result["entries"]} == {
        f"finding-{index}" for index in range(8)
    }



def test_large_memory_is_stored_but_read_is_optimized(tmp_path):
    content = "x" * 20_000
    published = publish_agent_memory(
        tmp_path,
        agent_id="writer",
        task_id="large",
        content=content,
    )
    result = read_agent_memory(tmp_path, task_id="large", max_chars=500)
    assert published["stored_chars"] == 20_000
    assert result["used_chars"] <= 500
    assert result["truncated"] is True


def test_invalid_soft_limits_fall_back_without_error(tmp_path):
    publish_agent_memory(tmp_path, agent_id="writer", content="note")
    result = read_agent_memory(tmp_path, limit=-999, max_chars=-5)
    assert result["status"] == "ok"
    assert result["optimized_limit"] == 1
    assert result["max_chars"] == 200


def test_task_passport_preserves_goal_and_supports_handoff(tmp_path):
    created = ensure_task_passport(
        tmp_path,
        task_id="branch:feature",
        goal="Fix login timeout",
    )
    assert created["passport"]["goal"] == "Fix login timeout"

    claimed = update_task_passport(
        tmp_path,
        task_id="branch:feature",
        agent_id="worker-1",
        status="in_progress",
        summary="Redis path isolated",
        next_action="Add timeout test",
        claim=True,
    )
    assert claimed["passport"]["owner_agent"] == "worker-1"
    assert claimed["passport"]["next_action"] == "Add timeout test"

    reread = read_task_passport(tmp_path, task_id="branch:feature")
    assert reread["passport"]["goal"] == "Fix login timeout"
    assert reread["passport"]["summary"] == "Redis path isolated"


def test_passport_redacts_secrets_without_rejecting_long_text(tmp_path):
    summary = "API_KEY=super-secret " + ("detail " * 1000)
    result = update_task_passport(
        tmp_path,
        task_id="secure",
        agent_id="worker",
        summary=summary,
    )
    assert "super-secret" not in result["passport"]["summary"]
    assert "[REDACTED]" in result["passport"]["summary"]
