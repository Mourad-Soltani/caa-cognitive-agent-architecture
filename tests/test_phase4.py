import json
import tempfile
import unittest
from pathlib import Path
from caa.agent import Agent
from caa.core.schemas import Task
from caa.memory.store import MemoryStore
from caa.models.client import MockModel
from caa.reflection.consolidate import consolidate
from eval import real_run
from eval.domains import MultiDomainStub
from eval.sql_domain import BROKEN, REFERENCE, build_sql_tasks, extract_sql, run_sql
from eval.stats import bootstrap_ci, paired_diff_ci


class StatsTests(unittest.TestCase):
    def test_ci_brackets_mean_and_degenerate_cases(self):
        m, lo, hi = bootstrap_ci([1, 0, 1, 1, 0, 1, 1, 1, 0, 1])
        self.assertTrue(lo <= m <= hi)
        self.assertEqual(bootstrap_ci([1, 1, 1]), (1.0, 1.0, 1.0))
        self.assertEqual(bootstrap_ci([]), (None, None, None))

    def test_paired_diff(self):
        m, lo, hi = paired_diff_ci([1] * 20, [0] * 20)
        self.assertEqual((m, lo, hi), (1.0, 1.0, 1.0))
        with self.assertRaises(ValueError):
            paired_diff_ci([1], [1, 0])

    def test_ci_shrinks_with_n(self):
        w = lambda n: (lambda r: r[2] - r[1])(bootstrap_ci([1, 0] * n))
        self.assertLess(w(200), w(10))


class SqlDomainTests(unittest.TestCase):
    def test_reference_passes_broken_fails(self):
        tasks = build_sql_tasks()
        self.assertEqual(len(tasks), 10)
        for t in tasks:
            n = t.meta["name"]
            self.assertEqual(t.meta["check"](REFERENCE[n])[0], "pass", n)
            self.assertEqual(t.meta["check"](BROKEN[n])[0], "fail", n)

    def test_checker_is_read_only_and_bounded(self):
        for bad in ("DROP TABLE employees", "SELECT 1; DROP TABLE employees", "DELETE FROM orders"):
            self.assertIsNotNone(run_sql(bad)[1], bad)
        _, err = run_sql("WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM r) SELECT COUNT(*) FROM r")
        self.assertIsNotNone(err)  # runaway query is interrupted, not hung

    def test_extract_sql_and_feedback(self):
        self.assertEqual(extract_sql("```sql\nSELECT 1;\n```"), "SELECT 1")
        t = build_sql_tasks()[0]
        verdict, note = t.meta["check"]("```sql\nSELECT nope FROM employees\n```")
        self.assertEqual(verdict, "fail")
        self.assertIn("SQL error", note)


class ConsolidateModel(MockModel):
    mode = "good"

    def complete(self, role, prompt, tier="fast"):
        if role == "consolidator":
            if self.mode == "bad":
                return "RULE: 1 nothing = 1 nothing"
            return "\n".join(l[2:] for l in prompt.splitlines() if l.startswith("- RULE:"))
        return super().complete(role, prompt, tier)


def rules_agent(mode="good", n_units=3):
    m = ConsolidateModel()
    m.mode = mode
    a = Agent(m, m, MemoryStore())
    units = [("zorb", "glim", 4), ("vex", "mool", 7), ("krin", "plod", 3)][:n_units]
    for x, y, n in units:
        t = Task(f"How many {y} in 3 {x}?", task_type="rules", meta={"expected": str(3 * n), "feedback": f"1 {x} = {n} {y}"})
        assert a.learn(t, a.handle(t))
    return a


class ConsolidationTests(unittest.TestCase):
    def test_good_consolidation_promotes_general_rule_and_retires_members(self):
        a = rules_agent()
        rep = consolidate(a, min_cluster=3)
        self.assertEqual(len(rep["promoted"]), 1)
        self.assertEqual(rep["promoted"][0]["after"], rep["promoted"][0]["before"])
        kinds = {r["kind"] for r in a.memory.db.execute("SELECT kind FROM facts WHERE active=1")}
        self.assertEqual(kinds, {"procedural"})
        hit = a.memory.recall("How many plod in 3 krin?")
        self.assertEqual(len(hit), 1)                 # identical texts collapsed to one context line
        self.assertIn("krin", hit[0]["text"])

    def test_bad_consolidation_is_rolled_back(self):
        a = rules_agent(mode="bad")
        before = {r["id"] for r in a.memory.db.execute("SELECT id FROM facts WHERE active=1")}
        rep = consolidate(a, min_cluster=3)
        self.assertEqual(rep["promoted"], [])
        self.assertEqual(len(rep["rejected"]), 1)
        after = {r["id"] for r in a.memory.db.execute("SELECT id FROM facts WHERE active=1")}
        self.assertEqual(before, after)                # members restored, bad rule inactive
        t = Task("How many glim in 5 zorb?", meta={"expected": "20"})
        self.assertEqual(a.handle(t).verifier, "pass")

    def test_small_clusters_are_skipped(self):
        rep = consolidate(rules_agent(n_units=2), min_cluster=3)
        self.assertEqual((rep["promoted"], rep["skipped"]), ([], ["rules"]))


class RealRunTests(unittest.TestCase):
    def run_small(self, out, budget=50.0, conds=("A", "C"), trials=2):
        return real_run.run_all(MultiDomainStub, list(conds), trials, real_run.PRICES, budget, 4, Path(out))

    def test_end_to_end_paired_arrays_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.run_small(d)
            agg = real_run.aggregate(run["trials"])
            a = real_run._pool(run["trials"], "A", "code", "held_after")
            c = real_run._pool(run["trials"], "C", "code", "held_after")
            self.assertEqual(len(a), len(c))           # same tasks, same order across conditions
            self.assertEqual(agg["conditions"]["A"]["rules"]["learn_retry"][0], 0.0)
            self.assertEqual(agg["conditions"]["C"]["rules"]["learn_retry"][0], 1.0)
            stage = real_run.assess(agg, real_model=False, truncated=False, n_tasks=48, autonomy=None)
            self.assertEqual(stage["qualified_stage"], 0)
            md = real_run.render({"model": "stub", "trials": 2, "per_domain": 4, "conds": ["A", "C"], "prices_set": False},
                                 run, agg, stage)
            self.assertIn("PLACEHOLDER prices", md)

    def test_resume_skips_completed_trials(self):
        with tempfile.TemporaryDirectory() as d:
            first = self.run_small(d)
            second = self.run_small(d)
            self.assertEqual((first["executed"], first["resumed"]), (4, 0))
            self.assertEqual((second["executed"], second["resumed"]), (0, 4))
            self.assertEqual(len(list(Path(d).glob("ckpt_*.json"))), 4)

    def test_budget_truncates_and_never_checkpoints(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.run_small(d, budget=1e-9, conds=("C",), trials=1)
            self.assertTrue(run["trials"][0]["truncated"])
            self.assertEqual(list(Path(d).glob("ckpt_*.json")), [])
            agg = real_run.aggregate(run["trials"])
            st = real_run.assess(agg, real_model=True, truncated=True, n_tasks=48, autonomy=None)
            self.assertEqual(st["qualified_stage"], 0)
            self.assertIn("truncated", st["note"])

    def test_real_model_with_strong_ci_evidence_reaches_stage_three(self):
        ci1, up = (1.0, 0.9, 1.0), (0.5, 0.2, 0.8)
        agg = {"vs_A": {"C": {"code": {"learn_retry": ci1}}},
               "uplift_heldout": {"C": {d: up for d in ("rules", "code", "planning", "sql")}},
               "forgetting": {"C": {d: (0.0, 0.0, 0.0) for d in ("rules", "code", "planning", "sql")}},
               "controls": {"C": {"before": (1.0, 1, 1), "after": (1.0, 1, 1)}}}
        auto = {"success_rate": 0.9, "awaiting_approval": 1}
        self.assertEqual(real_run.assess(agg, True, False, 48, auto)["qualified_stage"], 3)
        agg["uplift_heldout"]["C"]["sql"] = (0.1, -0.1, 0.3)       # CI crosses zero -> not significant
        agg["uplift_heldout"]["C"]["code"] = (0.1, -0.1, 0.3)
        self.assertEqual(real_run.assess(agg, True, False, 48, auto)["qualified_stage"], 1)

    def test_dry_run_prints_plan_without_calls(self):
        plan = real_run.main(["--model", "anthropic", "--dry-run", "--per-domain", "6", "--trials", "1"])
        self.assertGreater(plan["model_calls_upper_bound"], 0)


if __name__ == "__main__":
    unittest.main()
