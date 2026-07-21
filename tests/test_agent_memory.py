"""Tests for concurrent local agent memory."""

from concurrent.futures import ThreadPoolExecutor

from code_review_graph.agent_memory import (
    publish_agent_memory,
    read_agent_memory,
)


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
