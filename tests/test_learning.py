import unittest
from caa.agent import Agent
from caa.core.schemas import Task
from caa.memory.store import MemoryStore
from caa.models.client import MockModel
from eval.run_eval import CONDITIONS, run_condition


def task(k=3):
    return Task("How many glim in %d zorb?" % k,
                meta={"expected": str(4 * k), "feedback": "1 zorb = 4 glim"})


class LearningTests(unittest.TestCase):
    def test_fail_reflect_retry_transfer(self):
        a = Agent(MockModel(), MockModel(), MemoryStore())
        r1 = a.handle(task(3))
        self.assertEqual(r1.verifier, "fail")
        self.assertTrue(r1.escalated)  # low confidence escalated to slow path
        self.assertIsNotNone(a.learn(task(3), r1))
        self.assertEqual(a.handle(task(3)).verifier, "pass")   # retry
        self.assertEqual(a.handle(task(25)).verifier, "pass")  # transfer to new numbers

    def test_bad_lesson_not_promoted(self):
        a = Agent(MockModel(), MockModel(), MemoryStore())
        t = Task("How many glim in 3 zorb?", meta={"expected": "12", "feedback": "1 vex = 7 mool"})
        r = a.handle(t)
        self.assertIsNone(a.learn(t, r))  # lesson fails replay validation
        self.assertEqual(a.memory.recall("zorb glim"), [])

    def test_unverifiable_is_labeled(self):
        a = Agent(MockModel(), MockModel(), MemoryStore())
        self.assertEqual(a.handle(Task("What is 2 plus 2?")).verifier, "unverifiable")

    def test_eval_gate_c_beats_baselines_without_regression(self):
        rows = {n: run_condition(n, f) for n, f in CONDITIONS.items()}
        a, b, c = (rows[k] for k in ("A_no_memory", "B_memory_no_reflection", "C_full_caa"))
        self.assertGreater(c["transfer_success"], a["transfer_success"])
        self.assertGreater(c["transfer_success"], b["transfer_success"])
        self.assertGreaterEqual(c["control_success"], a["control_success"])


if __name__ == "__main__":
    unittest.main()
