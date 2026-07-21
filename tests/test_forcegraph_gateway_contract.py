"""Contract tests for the compact ForceGraph gateway surface."""

from code_review_graph import main as crg_main


def test_compact_profile_is_intentionally_tiny():
    assert crg_main.COMPACT_TOOL_NAMES == (
        "forcegraph_context_tool",
        "forcegraph_memory_tool",
        "detect_changes_tool",
        "build_or_update_graph_tool",
    )


def test_every_compact_tool_is_registered():
    for name in crg_main.COMPACT_TOOL_NAMES:
        assert getattr(crg_main, name, None) is not None
