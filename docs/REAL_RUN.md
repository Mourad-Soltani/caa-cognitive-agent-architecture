# Real-run runbook (turns the project from a plumbing demo into evidence)

## 0. Safety first
The harness EXECUTES model-written Python (code domain) and SQL (read-only, bounded). Code runs in a
subprocess with a minimal environment (API keys are NOT passed), CPU/memory limits and a timeout, but
there is no network or filesystem isolation. Run on a disposable VM/container with an egress allow-list
(only the API host) and no other secrets mounted. Do not run on a machine holding credentials you care about.

## 1. Preflight (5 minutes)
1. `python -m unittest discover -s tests` must pass (66 tests).
2. Prices: copy the CURRENT per-million-token prices for your fast and slow model from the provider's pricing page.
3. Dry run (no API calls, prints task-run count and a rough upper bound on calls and cost):
   `python -m eval.real_run --model anthropic --dry-run --per-domain 6 --trials 1`
4. Pilot (cheap, catches wiring/format problems):
   `ANTHROPIC_API_KEY=... python -m eval.real_run --model anthropic --conditions A,C --trials 1 --per-domain 6 --budget-usd 3 --price-fast IN,OUT --price-slow IN,OUT`
5. Fix anything odd in the pilot BEFORE the full run (model ignores the code-fence format, planner/critic roles ignored, etc.).

## 2. Full run
`ANTHROPIC_API_KEY=... python -m eval.real_run --model anthropic --trials 3 --budget-usd 25 --price-fast IN,OUT --price-slow IN,OUT --autonomy`
Interrupted? Re-run the same command with the same `--out`: finished (condition, trial) pairs are skipped.
Budget-truncated trials are excluded and the report states that no stage can be certified.

## 3. Read the report in this order
1. **Floor and ceiling.** Condition A pass rates. Near 100% = tasks too easy (nothing to learn). Near 0% = tasks or prompt format broken.
2. **Held-out uplift per domain (held_after - held_before), CI.** The generalisation metric. A lower bound above 0 in 3+ domains is what Stage 2 needs.
3. **vs A paired differences.** Does the loop beat no-memory? learn_retry only proves memory of seen tasks.
4. **Forgetting** (learn_retry - learn_final) near 0, and **controls** not regressing.
5. **Cost.** Compare C with D (search): is the gain worth the multiple?
6. Stage line. It is computed from CIs; do not override it.

## 4. Before publishing a number
- Record: model ids, date, task-set versions (code-v2, SQL 10, planning seed 3, rules seed 7), trial count, commit hash, prices used.
- Re-run once with a different `--trials` count or seed offset; a result that vanishes is noise.
- Publish the failures too (domains with no uplift). Selective reporting destroys the value of the report.
- Say what it is: a small multi-domain benchmark of a memory/reflection loop, not evidence of general intelligence.

## 5. Known limits
Hidden tests are fixed and public in this repo (rotate or add private tasks before comparing vendors). 80 or so tasks give wide CIs
on per-domain numbers. Token counts are estimated (chars/4) and the budget cap is only as good as the prices you pass. Lessons
are retrieved lexically (swap in a real embedder via CallableEmbedder). Consolidation clusters by task type only.
