import unittest
from caa.agent import Agent
from caa.memory.store import MemoryStore
from caa.models.metered import Metered
from caa.models.client import MockModel
from caa.router.tuning import tune_long_task_words
from eval.code_tasks import build_code_tasks
from eval.scripted import ScriptedCoder


class TunerTests(unittest.TestCase):
    def test_finds_threshold_where_fast_stops_working(self):
        rows = []
        for w in range(10, 120, 10):
            for i in range(20):
                ok = (i < 19) if w <= 60 else (i < 6)   # fast: 95% short, 30% long
                rows.append({"words": w, "routed": "fast", "escalated": 0 if ok else 1,
                             "verdict": "pass" if ok else "fail"})
                rows.append({"words": w, "routed": "slow", "escalated": 0,
                             "verdict": "pass" if i < 19 else "fail"})
        best = tune_long_task_words(rows)
        self.assertTrue(50 <= best["threshold"] <= 70, best)

    def test_needs_both_paths(self):
        self.assertIn("error", tune_long_task_words([{"words": 5, "routed": "fast", "escalated": 0, "verdict": "pass"}]))


class MeteredTests(unittest.TestCase):
    def test_counts_and_cost(self):
        m = Metered(MockModel())
        m.complete("executor", "What is 1 plus 2?", "fast")
        m.complete("executor", "What is 1 plus 2?", "slow")
        self.assertEqual(m.calls, {"fast": 1, "slow": 1})
        self.assertGreater(m.cost, 0)


class CodeLoopTests(unittest.TestCase):
    def test_code_fail_reflect_retry_with_real_execution(self):
        a = Agent(ScriptedCoder(), ScriptedCoder(), MemoryStore())
        t = build_code_tasks()[0]
        r1 = a.handle(t)
        self.assertEqual(r1.verifier, "fail")
        self.assertTrue(r1.note)                      # real test output captured as feedback
        self.assertIsNotNone(a.learn(t, r1))          # lesson validated by executing code on replay
        self.assertEqual(a.handle(t).verifier, "pass")

    def test_decisions_logged(self):
        a = Agent(MockModel(), MockModel(), MemoryStore())
        from caa.core.schemas import Task
        a.handle(Task("What is 2 plus 2?"))
        self.assertEqual(len(a.decisions.rows()), 1)


if __name__ == "__main__":
    unittest.main()
