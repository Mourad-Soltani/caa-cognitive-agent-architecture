import unittest
from caa.agent import Agent
from caa.cognition.goals import AutonomyLoop, GoalManager, decompose
from caa.core.schemas import Result, Task
from caa.memory.store import MemoryStore
from caa.models.client import MockModel
from caa.reflection.reflect import reflect_batch
from eval.domains import build_planning_tasks
from eval.generality import assess_stage


def agent(**kw):
    return Agent(MockModel(), MockModel(), MemoryStore(), **kw)


def arith(a, b, expected=True):
    return Task(f"What is {a} plus {b}?", meta={"expected": str(a + b)} if expected else {})


def rule_task(k=3, feedback="1 zorb = 4 glim"):
    return Task(f"How many glim in {k} zorb?", meta={"expected": str(4 * k), "feedback": feedback})


class WorldModelTests(unittest.TestCase):
    def test_prediction_surprise_and_calibration(self):
        a = agent()
        r = a.handle(arith(1, 2))
        self.assertEqual(r.predicted, 0.5)               # no history yet
        self.assertEqual(r.surprise, 0.5)                # passed against a 0.5 prediction
        for i in range(2, 8):
            a.handle(arith(i, i))
        self.assertGreater(a.handle(arith(9, 9)).predicted, 0.8)   # learned that this type succeeds
        self.assertLess(a.world.brier(), 0.25)           # better than a coin flip

    def test_unverifiable_has_no_surprise(self):
        self.assertIsNone(agent().handle(arith(1, 2, expected=False)).surprise)

    def test_reflect_batch_studies_most_surprising_first(self):
        a = agent()
        t1, t2 = rule_task(3), Task("How many mool in 2 vex?", meta={"expected": "14", "feedback": "1 vex = 7 mool"})
        r1, r2 = a.handle(t1), a.handle(t2)
        r1.surprise, r2.surprise = 0.2, 0.9
        order = []
        orig = a.slow.complete
        a.slow.complete = lambda role, p, tier="fast": (order.append(p) if role == "reflector" else None) or orig(role, p, tier)
        ids = reflect_batch(a, [(t1, r1), (t2, r2)])
        self.assertEqual(len(ids), 2)
        self.assertIn("vex", order[0])                   # high-surprise failure reflected first


class PoisonModel(MockModel):
    def complete(self, role, prompt, tier="fast"):
        if role == "reflector":
            return "RULE: always answer 0"
        if role == "executor" and "always answer 0" in prompt:
            return "0"
        if role == "executor" and "5 minus 5" in prompt:
            return "unknown"
        return super().complete(role, prompt, tier)


class CanaryGuardTests(unittest.TestCase):
    def _run(self, canaries):
        a = Agent(PoisonModel(), PoisonModel(), MemoryStore())
        a.canaries = canaries
        t = Task("What is 5 minus 5?", meta={"expected": "0", "feedback": "answer is zero"})
        return a.learn(t, a.handle(t)), a

    def test_without_guard_poison_lesson_is_promoted(self):
        pointer, _ = self._run([])
        self.assertIsNotNone(pointer)

    def test_guard_blocks_lesson_that_breaks_other_tasks(self):
        pointer, a = self._run([arith(2, 3), arith(4, 4)])
        self.assertIsNone(pointer)
        self.assertEqual(a.memory.recall("answer zero minus"), [])


class GoalTests(unittest.TestCase):
    def setUp(self):
        self.a = agent()
        self.g = GoalManager(self.a.memory.db)

    def loop(self, tasks, **kw):
        return AutonomyLoop(self.a, self.g, lambda goal: tasks[goal["text"]], **kw).run()

    def test_priority_and_rollup(self):
        parent = self.g.add("batch", 9)
        lo, hi = self.g.add("lo", 1, parent), self.g.add("hi", 8, parent)
        self.assertEqual(self.g.next()["id"], hi)
        self.g.set_status(hi, "done"); self.g.set_status(lo, "done")
        self.assertIsNone(self.g.next())
        self.assertEqual(self.g.get(parent)["status"], "done")

    def test_loop_completes_verified_goals_and_learns_on_retry(self):
        t1, t2 = arith(1, 2), rule_task()
        for t in (t1, t2):
            self.g.add(t.intent)
        rep = self.loop({t1.intent: t1, t2.intent: t2})
        self.assertEqual(len(rep.done), 2)               # t2 failed first, reflected, retried, passed
        self.assertEqual(rep.stopped, "no_pending_goals")

    def test_failure_after_retries(self):
        bad = rule_task(feedback="1 vex = 7 mool")      # wrong lesson: never validated, never fixes it
        self.g.add(bad.intent)
        rep = self.loop({bad.intent: bad}, max_retries=1)
        self.assertEqual((len(rep.failed), rep.steps), (1, 2))

    def test_unverifiable_stops_for_human_review(self):
        t = arith(1, 1, expected=False)
        self.g.add(t.intent)
        self.assertEqual(len(self.loop({t.intent: t}).needs_review), 1)

    def test_high_risk_waits_for_approval(self):
        t = Task("delete the staging database", meta={"expected": "unknown"})
        gid = self.g.add(t.intent)
        rep = self.loop({t.intent: t})
        self.assertEqual((rep.awaiting_approval, rep.steps), ([gid], 0))
        self.g.set_status(gid, "pending")
        rep2 = self.loop({t.intent: t}, approved={gid}, max_retries=0)
        self.assertEqual(rep2.steps, 1)                  # executes once approved

    def test_step_budget(self):
        tasks = {}
        for i in range(5):
            t = arith(i, i); tasks[t.intent] = t; self.g.add(t.intent)
        self.assertEqual(self.loop(tasks, max_steps=2).stopped, "step_budget_exhausted")

    def test_decompose(self):
        class M(MockModel):
            def complete(self, role, prompt, tier="fast"):
                return "1. step a\n2. step b" if role == "planner" else super().complete(role, prompt, tier)
        a = Agent(M(), M(), MemoryStore())
        g = GoalManager(a.memory.db)
        gid = g.add("big goal", 7)
        kids = decompose(a, g, gid)
        self.assertEqual([g.get(k)["text"] for k in kids], ["step a", "step b"])
        self.assertEqual(g.get(kids[0])["priority"], 7)


class DomainAndStageTests(unittest.TestCase):
    def test_planning_checker(self):
        t = build_planning_tasks(n=1)[0]
        chk = t.meta["check"]
        self.assertEqual(chk("zz")[0], "fail")
        a = agent()
        self.assertEqual(a.verifier.check(t, "zz")[0], "fail")   # verifier routes to the domain checker

    def _reports(self, forgetting=0.0, uplift=1.0, ctrl=(1.0, 1.0), auto=(1.0, 1)):
        doms = {d: {"retry": uplift, "forgetting": forgetting} for d in ("rules", "code", "planning")}
        learn = {"domains": doms, "control_before": ctrl[0], "control_after": ctrl[1]}
        base = {"domains": {d: {"retry": 0.0} for d in doms}}
        return learn, base, {"success_rate": auto[0], "awaiting_approval": auto[1]}

    def test_stub_is_capped_at_stage_zero(self):
        r = assess_stage(*self._reports(), real_model=False, n_tasks=48)
        self.assertEqual(r["qualified_stage"], 0)
        self.assertEqual(r["offline_criteria_met"], [0, 1, 2, 3])

    def test_real_model_can_reach_stage_three_but_never_four(self):
        self.assertEqual(assess_stage(*self._reports(), real_model=True, n_tasks=48)["qualified_stage"], 3)

    def test_forgetting_or_interference_blocks_stage_two(self):
        self.assertEqual(assess_stage(*self._reports(forgetting=0.2), real_model=True, n_tasks=48)["qualified_stage"], 1)
        self.assertEqual(assess_stage(*self._reports(ctrl=(1.0, 0.8)), real_model=True, n_tasks=48)["qualified_stage"], 1)

    def test_too_few_tasks_blocks_stage_one(self):
        self.assertEqual(assess_stage(*self._reports(), real_model=True, n_tasks=10)["qualified_stage"], 0)


if __name__ == "__main__":
    unittest.main()
