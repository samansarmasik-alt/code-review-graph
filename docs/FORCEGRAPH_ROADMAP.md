# ForceGraph development roadmap

This roadmap separates implemented upstream capabilities from planned
ForceGraph-specific work. A roadmap item is not considered shipped until its
tests, documentation, and compatibility checks are complete.

## Phase 0 — Fork foundation

- [x] Preserve upstream Git history and MIT license
- [x] Establish ForceGraph identity and attribution
- [x] Retain upstream CLI compatibility during the transition
- [x] Record the initial upstream baseline
- [x] Add a one-command, AI-readable installation and verification flow
- [x] Add tool-neutral auto-detection and a vendor-neutral MCP manifest
- [ ] Add a dedicated ForceGraph release and compatibility policy

## Phase 1 — Context bundle protocol

- [ ] Define a versioned JSON schema for targeted AI context bundles
- [ ] Include relevant symbols, callers, callees, tests, flows, and risk evidence
- [ ] Enforce configurable response token and file budgets
- [ ] Add deterministic receipts explaining why every context item was selected
- [x] Add bounded local shared memory and handoffs for concurrent terminal agents
- [x] Auto-resolve shared-memory task and agent identity without user commands
- [ ] Add secret and ignored-file filtering before bundle generation
- [x] Expose bilingual task-routed compact context through MCP
- [ ] Expose versioned portable bundle generation through CLI and MCP

## Phase 2 — Universal agent integration

- [ ] Publish portable context bundle and review JSON schemas
- [ ] Add adapter examples for generic MCP clients and agent frameworks
- [x] Ship a compact default MCP capability profile for connected agents
- [ ] Expose graph freshness and capability negotiation through MCP
- [ ] Support graceful fallback when the graph is missing or stale
- [ ] Keep all vendor-specific adapters optional and independently testable

## Phase 3 — Review intelligence

- [ ] Compare pre-change and post-change graph snapshots
- [ ] Improve confidence scoring for extracted, inferred, and ambiguous edges
- [ ] Detect risky public API and configuration changes
- [ ] Rank test gaps by affected execution flow
- [ ] Produce machine-readable and human-readable review reports

## Phase 4 — Developer experience

- [ ] Turkish and English first-run experience
- [ ] Reliable Windows installation and path handling
- [x] Add the `forcegraph` command alias without breaking the upstream CLI
- [ ] Publish a ForceGraph-native package name with a migration policy
- [ ] Lightweight local dashboard for architecture and impact exploration
- [ ] Incremental performance benchmarks on large mixed-language repositories

## Engineering rules

Every ForceGraph-specific feature should include:

1. Unit tests for its core behaviour.
2. At least one integration or end-to-end test when it crosses module boundaries.
3. Token, latency, and correctness evidence for optimisation claims.
4. A migration path for persisted SQLite data or configuration changes.
5. Documentation that distinguishes implemented behaviour from planned work.
