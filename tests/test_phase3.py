import unittest
from caa.agent import Agent
from caa.core.schemas import Task
from caa.deliberation.code_verifier import CodeVerifier
from caa.deliberation.plan_search import SearchExecutor
from caa.memory.store import MemoryStore
from eval import retrieval_eval
from eval.code_tasks import BROKEN, REFERENCE, build_code_tasks
from eval.scripted import ScriptedCoder


def task(name):
    return next(t for t in build_code_tasks() if t.meta["name"] == name)


class ScoreTestsTests(unittest.TestCase):
    def test_partial_credit_and_invalid(self):
        v = CodeVerifier(timeout=3)
        tests = "assert f(1)==1\nassert f(2)==4\nassert f(3)==9"
        r = v.score_tests("def f(x):\n    return x*x if x<3 else 0", tests)
        self.assertEqual((r["passed"], r["total"]), (2, 3))
        self.assertEqual(v.score_tests("def f(x): return x", "assert (")["total"], 0)
        self.assertEqual(v.score_tests("def f(:", tests)["passed"], 0)

    def test_infinite_loop_scores_zero(self):
        r = CodeVerifier(timeout=2).score_tests("def f(x):\n    while True: pass", "assert f(1)==1")
        self.assertEqual(r["passed"], 0)


class SearchTests(unittest.TestCase):
    def test_selects_the_passing_candidate(self):
        t = task("balanced_brackets")
        out, info = SearchExecutor(ScriptedCoder(), n=3).run(t.intent, "")
        self.assertEqual(info.chosen, 1)           # candidate 2 of 3
        self.assertTrue(info.discriminative)
        self.assertEqual(CodeVerifier().check(t, out)[0], "pass")  # hidden tests agree

    def test_fallback_when_selftests_cannot_discriminate(self):
        t = task("lru_cache")                       # scripted test_writer has no single-line asserts
        _, info = SearchExecutor(ScriptedCoder(), n=3).run(t.intent, "")
        self.assertEqual(info.chosen, 0)

    def test_fallback_on_invalid_tests(self):
        class M(ScriptedCoder):
            def complete(self, role, prompt, tier="fast"):
                return "```python\nassert (\n```" if role == "test_writer" else super().complete(role, prompt, tier)
        _, info = SearchExecutor(M(), n=3).run(task("fizzbuzz").intent, "")
        self.assertEqual((info.chosen, info.tests_total), (0, 0))
        self.assertTrue(info.fallback)

    def test_repair_round_can_fix(self):
        good = "def f(x):\n    return x + 1"
        bad = "def f(x):\n    return x"

        class M:
            calls = {"fast": 0, "slow": 0}
            def complete(self, role, prompt, tier="fast"):
                if role == "test_writer":
                    return "```python\nassert f(1)==2\nassert f(2)==3\n```"
                return good if "REPAIR:" in prompt else bad
        out, info = SearchExecutor(M(), n=2, repair_rounds=1).run("make f increment", "")
        self.assertTrue(info.repaired)
        self.assertIn("x + 1", out)

    def test_agent_with_search_escalates_and_passes(self):
        a = Agent(ScriptedCoder(), ScriptedCoder(), MemoryStore(), search_n=3)
        r = a.handle(task("balanced_brackets"))
        self.assertTrue(r.escalated)
        self.assertEqual(r.verifier, "pass")
        self.assertEqual(len(a.search_log), 1)

    def test_weak_selftests_can_pick_a_wrong_candidate(self):
        """Documented limitation: self-tests that miss the bug cannot separate candidates."""
        t = task("valid_ipv4")   # scripted visible tests never probe leading zeros
        out, info = SearchExecutor(ScriptedCoder(), n=3).run(t.intent, "")
        self.assertFalse(info.discriminative)
        self.assertEqual(CodeVerifier().check(t, out)[0], "fail")


class RetrievalTests(unittest.TestCase):
    def test_v1_cuts_leakage_without_losing_recall(self):
        v0, v1 = retrieval_eval.run("v0"), retrieval_eval.run("v1")
        for q in ("exact", "short", "no_name"):
            self.assertLess(v1[q]["leakage"], v0[q]["leakage"] / 5, q)
            self.assertGreaterEqual(v1[q]["own_recall"], 0.95, q)
            self.assertGreaterEqual(v1[q]["p@1"], 0.95, q)

    def test_novel_task_leakage_is_bounded(self):
        v0, v1 = retrieval_eval.run_novel("v0"), retrieval_eval.run_novel("v1")
        self.assertLess(v1["mean_hits"], v0["mean_hits"] / 10)
        self.assertLess(int(v1["novel_queries_with_any_hit"].split("/")[0]), 12)  # of 32; related tasks may legitimately match

    def test_pluggable_embedder(self):
        from caa.memory.retrieval import CallableEmbedder
        calls = []
        emb = CallableEmbedder(lambda s: (calls.append(s), [1.0, 0.0, 0.0])[1])
        m = MemoryStore(embedder=emb)
        m.promote("alpha rule", tags="alpha")
        self.assertTrue(m.recall("alpha")); self.assertTrue(calls)


class TaskSetTests(unittest.TestCase):
    def test_size_and_self_consistency(self):
        ts = build_code_tasks()
        self.assertGreaterEqual(len(ts), 30)
        self.assertEqual(len({t.meta["name"] for t in ts}), len(ts))
        self.assertEqual(set(REFERENCE), set(BROKEN))


if __name__ == "__main__":
    unittest.main()
