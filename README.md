# CAA: Cognitive Agent Architecture (v0.5)

Memory + reflection + router loop with a real-run harness that produces defensible numbers (bootstrap CIs, held-out transfer, budget-aware stage gates).

## Quick start

```bash
# Offline wiring checks (no API key, no network)
python -m eval.run_code --model scripted          # 32 code tasks, conditions A/B/C/D
python -m eval.real_run --model stub --trials 2 --per-domain 6
python -m eval.generality                         # multi-domain scorecard + stage gate
python -m pytest tests/ -q                        # 66 tests

# Real model (see docs/REAL_RUN.md)
python -m eval.real_run --model anthropic --dry-run --per-domain 6 --trials 1
ANTHROPIC_API_KEY=... python -m eval.real_run --model anthropic \
  --conditions A,C --trials 1 --per-domain 6 --budget-usd 3 \
  --price-fast IN,OUT --price-slow IN,OUT
```

## What exists

| Module | State |
|---|---|
| core/schemas, text | done |
| memory/store (SQLite episodic + facts, hybrid recall, prune, tombstone rollback) | done, **v1** retrieval |
| router (risk, skill cache, fresh data, length) | done, thresholds untuned on real data |
| workspace (planner/executor/critic) | minimal |
| deliberation/verifier + code_verifier | done (subprocess + rlimits; **not** a network sandbox) |
| metacognition | heuristic confidence + escalation |
| reflection (lesson → replay validation → promote) + consolidate | done, rollback-tested |
| models/metered | done; PRICES are placeholders |
| eval/real_run | repeated trials, CIs, held-out, budget, resume, stage gate |
| domains | rules, code (32), planning, **SQL (10)** |
| cognition (world model, goals, autonomy) | AGI-layer scaffolding |

## Phase 4 highlights (this release)

- **Real-run harness**: 95 % bootstrap CIs, paired vs baseline, budget cap, resumable checkpoints, truncated trials excluded.
- **Held-out transfer**: learn half vs held-out half per domain; held-out uplift is the generalization metric.
- **CI stage gate**: lower bound of CI must be > 0; stub / budget-truncated runs cannot exceed Stage 0.
- **SQL domain**: 10 tasks, read-only in-memory SQLite, op-limited, objective checker.
- **Skill consolidation**: case lessons → one general rule; real-retrieval re-test; full rollback on regression.
- **Secret isolation**: model code runs with a minimal environment; API keys are invisible (tested).

See `CHANGELOG.md` and `docs/REAL_RUN.md`.

## Caveat

The offline suite runs on `MockModel` / stub. It proves plumbing (lesson transfer, rejection of bad lessons, controls do not regress). It does **not** measure real intelligence. Real numbers require `AnthropicModel` (or another provider) plus a task set where the base model genuinely fails.

## Not built yet

Container / network sandbox for untrusted code, real embeddings (pgvector), procedural skill compilation, calibration curves on real data, parallel agents, cross-type abstraction in consolidation.

## AGI layer

See `docs/AGI_ARCHITECTURE.md` for the capability map, stage gates, and falsification criteria. Stub results are hard-capped at Stage 0 by design.

## License / contributing

Experimental research code. Run untrusted model output only inside a disposable environment with an egress allow-list.
