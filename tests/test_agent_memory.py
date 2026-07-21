"""Tests for concurrent local agent memory."""

from concurrent.futures import ThreadPoolExecutor

from code_review_graph.agent_memory import (
    publish_agent_memory,
    read_agent_memory,
    resolve_agent_id,
    resolve_task_id,
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
