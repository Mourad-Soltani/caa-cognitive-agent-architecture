import unittest
from caa.core.schemas import Task
from caa.router.router import Router


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.r = Router()

    def test_risky_goes_slow(self):
        self.assertEqual(self.r.route(Task("delete all user records"), []).path, "slow")

    def test_cached_skill_goes_fast(self):
        hit = [{"kind": "procedural", "score": 0.9, "text": "skill"}]
        self.assertEqual(self.r.route(Task("do the weekly report"), hit).path, "fast")

    def test_fresh_data_tool_first(self):
        self.assertEqual(self.r.route(Task("what is the latest release"), []).path, "tool_first")

    def test_long_goes_slow_short_fast(self):
        self.assertEqual(self.r.route(Task("word " * 50), []).path, "slow")
        self.assertEqual(self.r.route(Task("add 2 and 3"), []).path, "fast")


if __name__ == "__main__":
    unittest.main()
