# CAA as an AGI Architecture: staged, measurable, honest

## 1. Framing
No architecture becomes AGI by being labelled one. What a codebase can do is (a) implement the
mechanisms general intelligence appears to need, (b) measure generality instead of asserting it,
and (c) refuse to claim a stage the evidence does not support. This document does those three things.

Working definition: **a system that learns new tasks across many domains, quickly, from little
experience, without forgetting or breaking what it already does, and pursues goals autonomously
within verifiable limits.** Performance (how well) and generality (how broadly) are separate axes; both are measured.

## 2. Capability map (what general intelligence needs -> where it lives)

| Capability | Module | Status |
|---|---|---|
| Working / episodic / semantic / procedural memory | memory/store, retrieval | built (v1 retrieval; lexical + pluggable embedder) |
| Fast vs deliberate reasoning | router, workspace, plan_search | built; thresholds untuned on real data |
| Verification against ground truth | verifier (checker > tests > expected > unverifiable) | built; domain-pluggable |
| Learning from experience without retraining | reflection + replay-validated promotion | built |
| **Continual learning without interference** | canary guard in reflection | **new** |
| **Prediction and surprise (predictive processing)** | cognition/world_model | **new**, baseline predictor |
| **Calibration** | Brier score over predictions vs verified outcomes | **new** |
| **Persistent goals, bounded autonomy** | cognition/goals (GoalManager, AutonomyLoop) | **new** |
| **Domain generality** | eval/domains registry + checkers | **new**: rules, code, planning |
| Learned world model (not a pass-rate table) | -- | NOT built |
| Grounded perception and embodied action | -- | NOT built |
| Cross-domain abstraction (transferring a skill, not a fact) | reflection/consolidate | **partial**: validated per-task-type consolidation; no cross-type abstraction |
| Open-ended self-directed goal formation | -- | NOT built (goals are given, not invented) |

## 3. Architecture

```
 Goals (persistent stack, priorities, approval) --> AutonomyLoop (step budget, retries)
        |                                                   |
        v                                                   v
 Perception -> Router -> [fast | workspace | plan_search] -> Verifier (domain checker / tests / answer)
        ^          ^              |                              |
        |          |      WorldModel.predict() --------+         v
        |          |                                   +--> surprise, Brier calibration
        |          +---- Memory (episodic, semantic, procedural; tombstoned, versioned)
        |                          ^
        +--- Reflection <----------+  lesson -> replay-validate -> CANARY GUARD -> promote
```

Design rules: verified outcomes only close goals; unverifiable work stops for a human; high-risk
actions wait for approval; every memory write is reversible; every claim of progress is a number.

## 4. Domain interface (how generality is added)
A domain is a list of `Task` objects, each carrying exactly one verification path in `meta`:
`check` (callable returning `(verdict, note)`), `tests` (executed asserts) or `expected` (exact answer).
Adding a domain = writing tasks + a checker. No change to agent, memory or reflection code.
Current domains: **rules** (exact answer), **code** (32 tasks, executed tests), **planning** (property checker),
**sql** (10 tasks, executed read-only on SQLite, row comparison).

## 5. Stage gates (what each stage requires; enforced by `assess_stage`)

| Stage | Criterion | Evidence needed |
|---|---|---|
| 0 Scaffold | Loop works end to end | offline tests (done) |
| 1 Validated | Real model, 30+ tasks, full loop beats no-memory baseline in code | `eval.run_code --model anthropic` |
| 2 Multi-domain | Uplift >= 0.2 in 3+ domains, forgetting <= 0.05, controls not regressed | `eval.generality` on a real model |
| 3 Autonomous | Goal loop success >= 80% on verified goals, approval policy enforced | autonomy demo on a real model |
| 4 General | Zero-shot on UNSEEN domains + fast adaptation, compared with human baselines | not assessable here; needs human-baseline data |

The gate caps any stub-model result at Stage 0, even when its criteria are met offline.

## 6. Current status
Stage 0 certified. Stage 1-3 criteria are met offline on the stub (see `eval.generality`), which only
proves plumbing. Stage 4 is unassessed and is the part nobody has demonstrated.

## 7. What would falsify the approach
- Real-model uplift in code is ~0: reflection adds nothing beyond a good prompt.
- Uplift appears in one domain only: lessons are facts, not transferable skills.
- Forgetting or interference grows with lesson count: memory degrades the agent.
- Brier score stays near 0.25: the system cannot predict its own success.
- Autonomy success depends on a human fixing unverifiable steps: the loop is a supervised workflow.

## 8. Risks
Overclaiming (use stage language, never "AGI achieved"); reward hacking (agent optimises the checker, so
rotate hidden tests); unsafe autonomy (sandbox, approvals, spend caps in code); poisoned or stale memory
(provenance, tombstones, canary guard); evaluation leakage (hidden tests never reach selection).

## 9. Roadmap
1. Real-model run, 30+ tasks, publish A/B/C/D with confidence intervals (Stage 1).
2. Add 2-3 real domains with objective checkers (SQL queries vs expected rows, data transformations, API workflows) (Stage 2).
3. Replace the pass-rate predictor with a learned one; track calibration over time.
4. Skill abstraction: compile repeated lessons into parameterised procedures and test transfer to unseen tasks.
5. Held-out unseen-domain evaluation with human baselines (Stage 4 evidence).
