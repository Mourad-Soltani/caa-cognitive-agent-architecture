# Changelog

## 0.5.0 — 2026-10-17

### Added
- **Real-run harness** (`eval/real_run.py`): repeated trials, 95% bootstrap CIs, paired comparisons vs baseline A, budget cap, resumable checkpoints, truncated-trial exclusion.
- **Held-out transfer**: each domain split into learn / held-out halves; held-out uplift is the generalization metric.
- **CI-based stage gate**: stage requires CI lower bound > 0; stub and budget-truncated runs stay at Stage 0.
- **SQL domain** (10 tasks): read-only in-memory SQLite with op limit; objective checker; self-tested.
- **Skill consolidation** (`caa/reflection/consolidate.py`): case lessons → one general procedural rule; re-test via real retrieval; full transactional rollback on any regression (mutation-tested).
- **Env isolation for model code**: `CodeVerifier` runs with minimal `_SAFE_ENV` so `ANTHROPIC_API_KEY` is invisible (tested).
- **Runbook**: `docs/REAL_RUN.md` (preflight → pilot → full run → how to read the report).
- World-model predictions + surprise, goal stack + bounded autonomy, canary guard against lesson interference (AGI layer).

### Changed
- Retrieval defaults to v1 (IDF lexical + pluggable embedder, relative gate, min_score 0.3). Identical rule texts are collapsed.
- Memory promote/rollback is tombstone-based (never hard-delete).
- Versioning and packaging metadata aligned to 0.5.0.

### Security / safety
- Deliberately disabled consolidation safety → rollback test fails (guard is real).
- Model-written code never inherits secrets from the parent environment.

### Known limits (unchanged)
- No network/filesystem isolation for the code executor (use a disposable container).
- Consolidation clusters by task_type only; no cross-type abstraction yet.
- Cost caps depend on caller-supplied prices; built-in prices are placeholders.
- Stub held-out uplift can inflate on planning/SQL due to shared boilerplate; CIs + held-out design are the intended guard for real models.

## 0.1.x — earlier
Phases 0–3 scaffolding: memory store, router, reflection, code verifier, plan search, multi-domain eval, retrieval v0/v1.
