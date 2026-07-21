"""Tests for the one-command ForceGraph onboarding flow."""

from __future__ import annotations

import argparse
import json
import sys
from unittest.mock import patch

from code_review_graph import cli


def _args(repo, **overrides):
    values = {
        "repo": str(repo),
        "platform": "codex",
        "fast": False,
        "no_build": False,
        "dry_run": False,
        "no_skills": False,
        "no_hooks": False,
        "no_instructions": False,
        "yes": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_quickstart_installs_builds_and_writes_receipt(monkeypatch, tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    data_dir = repo / ".code-review-graph"

    monkeypatch.setattr(
        cli,
        "_handle_init",
        lambda args: {
            "repo_root": str(repo),
            "configured_platforms": ["Codex"],
            "dry_run": False,
        },
    )
    monkeypatch.setattr(
        "code_review_graph.incremental.get_db_path",
        lambda root: data_dir / "graph.db",
    )
    build_result = {
        "files_parsed": 12,
        "total_nodes": 34,
        "total_edges": 56,
        "errors": [],
    }
    monkeypatch.setattr(
        "code_review_graph.tools.build.build_or_update_graph",
        lambda **kwargs: build_result,
    )

    receipt = cli._handle_quickstart(_args(repo))

    saved = json.loads((data_dir / "quickstart-receipt.json").read_text(encoding="utf-8"))
    assert receipt == saved
    assert saved["status"] == "ready"
    assert saved["configured_platforms"] == ["Codex"]
    assert saved["graph"] == {
        "built": True,
        "files": 12,
        "nodes": 34,
        "edges": 56,
        "errors": 0,
        "postprocess": "full",
    }
    assert saved["restart_required"] is True
    assert "ForceGraph is ready." in capsys.readouterr().out


def test_quickstart_fast_uses_minimal_postprocessing(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    calls = []
    monkeypatch.setattr(
        cli,
        "_handle_init",
        lambda args: {
            "repo_root": str(repo),
            "configured_platforms": [],
            "dry_run": False,
        },
    )
    monkeypatch.setattr(
        "code_review_graph.incremental.get_db_path",
        lambda root: repo / ".code-review-graph" / "graph.db",
    )

    def _build(**kwargs):
        calls.append(kwargs)
        return {"files_parsed": 1, "total_nodes": 2, "total_edges": 3}

    monkeypatch.setattr("code_review_graph.tools.build.build_or_update_graph", _build)

    receipt = cli._handle_quickstart(_args(repo, fast=True))

    assert calls == [
        {
            "full_rebuild": True,
            "repo_root": str(repo.resolve()),
            "postprocess": "minimal",
        }
    ]
    assert receipt["graph"]["postprocess"] == "minimal"


def test_quickstart_dry_run_never_builds(monkeypatch, tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(
        cli,
        "_handle_init",
        lambda args: {
            "repo_root": str(repo),
            "configured_platforms": ["Codex"],
            "dry_run": True,
        },
    )

    receipt = cli._handle_quickstart(_args(repo, dry_run=True))

    assert receipt["status"] == "dry-run"
    assert receipt["graph_built"] is False
    assert "Would build the graph" in capsys.readouterr().out
    assert not (repo / ".code-review-graph").exists()


def test_quickstart_cli_dispatches_without_confirmation(tmp_path):
    argv = [
        "code-review-graph",
        "quickstart",
        "--repo",
        str(tmp_path),
        "--platform",
        "codex",
        "--no-build",
    ]
    with patch.object(sys, "argv", argv):
        with patch("code_review_graph.cli._handle_quickstart") as handler:
            cli.main()

    args = handler.call_args.args[0]
    assert args.repo == str(tmp_path)
    assert args.platform == "codex"
    assert args.no_build is True
    assert args.yes is True


def test_connect_writes_vendor_neutral_mcp_config(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    data_dir = repo / ".code-review-graph"
    monkeypatch.setattr(
        cli,
        "_handle_init",
        lambda args: {
            "repo_root": str(repo),
            "configured_platforms": [],
            "dry_run": False,
        },
    )
    monkeypatch.setattr(
        "code_review_graph.incremental.get_db_path",
        lambda root: data_dir / "graph.db",
    )
    monkeypatch.setattr(
        "code_review_graph.skills._build_server_entry",
        lambda platform, repo_root=None: {
            "command": "forcegraph",
            "args": ["serve", "--auto-watch"],
            "cwd": str(repo_root),
            "type": "stdio",
        },
    )

    args = _args(repo, command="connect", no_build=True, platform="all")
    receipt = cli._handle_quickstart(args)

    config_path = data_dir / "mcp-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["schema_version"] == 1
    assert config["mcpServers"]["code-review-graph"]["command"] == "forcegraph"
    assert config["mcpServers"]["code-review-graph"]["args"][-1] == "--auto-watch"
    assert receipt["universal_mcp_config"] == str(config_path)


def test_connect_cli_defaults_to_auto_detection(tmp_path):
    argv = ["forcegraph", "connect", "--repo", str(tmp_path), "--no-build"]
    with patch.object(sys, "argv", argv):
        with patch("code_review_graph.cli._handle_quickstart") as handler:
            cli.main()

    args = handler.call_args.args[0]
    assert args.command == "connect"
    assert args.platform == "all"
    assert args.yes is True
