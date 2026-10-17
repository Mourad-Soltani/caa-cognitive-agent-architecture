import unittest
from caa.memory.store import MemoryStore


class MemoryTests(unittest.TestCase):
    def test_promote_recall_rollback(self):
        m = MemoryStore()
        fid = m.promote("RULE: 1 zorb = 4 glim")
        m.promote("RULE: 1 vex = 7 mool")
        hits = m.recall("How many glim in 5 zorb?")
        self.assertEqual(hits[0]["id"], fid)
        self.assertEqual(len(hits), 1)  # unrelated rule filtered out
        m.rollback(fid)
        self.assertEqual(m.recall("How many glim in 5 zorb?"), [])

    def test_dedup(self):
        m = MemoryStore()
        self.assertEqual(m.promote("same"), m.promote("same"))

    def test_prune_retires_unused(self):
        m = MemoryStore()
        fid = m.promote("never used fact", trust=0.21)
        self.assertEqual(m.prune(decay=0.9, floor=0.2), [fid])
        self.assertEqual(m.recall("never used fact"), [])

    def test_episode_log(self):
        m = MemoryStore()
        m.write_episode({"intent": "x", "status": "fail"})
        self.assertEqual(len(m.episodes("fail")), 1)


class DedupSituationTest(unittest.TestCase):
    def test_same_text_different_situation_kept_separate(self):
        m = MemoryStore()
        a = m.promote("check edge cases", tags="fizzbuzz task")
        b = m.promote("check edge cases", tags="palindrome task")
        self.assertNotEqual(a, b)
        self.assertEqual(m.recall("palindrome")[0]["id"], b)


if __name__ == "__main__":
    unittest.main()
