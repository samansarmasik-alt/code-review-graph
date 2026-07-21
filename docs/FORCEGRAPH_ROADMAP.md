# ForceGraph development roadmap

This roadmap separates implemented upstream capabilities from planned
ForceGraph-specific work. A roadmap item is not considered shipped until its
tests, documentation, and compatibility checks are complete.

## Phase 0 — Fork foundation

- [x] Preserve upstream Git history and MIT license
- [x] Establish ForceGraph identity and attribution
- [x] Retain upstream CLI compatibility during the transition
- [x] Record the initial upstream baseline
- [ ] Add a dedicated ForceGraph release and compatibility policy

## Phase 1 — Context bundle protocol

- [ ] Define a versioned JSON schema for targeted AI context bundles
- [ ] Include relevant symbols, callers, callees, tests, flows, and risk evidence
- [ ] Enforce configurable token and file budgets
- [ ] Add deterministic receipts explaining why every context item was selected
- [ ] Add secret and ignored-file filtering before bundle generation
- [ ] Expose bundle generation through CLI and MCP

## Phase 2 — ForceCode integration

- [ ] Add `/graph`, `/impact`, and `/review` ForceCode commands
- [ ] Connect graph results to ForceContext candidate retrieval
- [ ] Send evidence and test gaps to the Execution Kernel
- [ ] Persist graph version and context receipt in `last-run.json`
- [ ] Support graceful fallback when the graph is missing or stale

## Phase 3 — Review intelligence

- [ ] Compare pre-change and post-change graph snapshots
- [ ] Improve confidence scoring for extracted, inferred, and ambiguous edges
- [ ] Detect risky public API and configuration changes
- [ ] Rank test gaps by affected execution flow
- [ ] Produce machine-readable and human-readable review reports

## Phase 4 — Developer experience

- [ ] Turkish and English first-run experience
- [ ] Reliable Windows installation and path handling
- [ ] ForceGraph-native command and package names with migration aliases
- [ ] Lightweight local dashboard for architecture and impact exploration
- [ ] Incremental performance benchmarks on large mixed-language repositories

## Engineering rules

Every ForceGraph-specific feature should include:

1. Unit tests for its core behaviour.
2. At least one integration or end-to-end test when it crosses module boundaries.
3. Token, latency, and correctness evidence for optimisation claims.
4. A migration path for persisted SQLite data or configuration changes.
5. Documentation that distinguishes implemented behaviour from planned work.

