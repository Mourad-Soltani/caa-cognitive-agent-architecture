import unittest
from caa.core.schemas import Task
from caa.deliberation.code_verifier import CodeVerifier
from eval.code_tasks import BROKEN, REFERENCE, build_code_tasks


class CodeVerifierTests(unittest.TestCase):
    def setUp(self):
        self.v = CodeVerifier(timeout=3)
        self.tasks = {t.meta["name"]: t for t in build_code_tasks()}

    def test_reference_solutions_pass(self):
        for n, t in self.tasks.items():
            self.assertEqual(self.v.check(t, REFERENCE[n])[0], "pass", n)

    def test_broken_solutions_fail_with_feedback(self):
        for n, t in self.tasks.items():
            verdict, note = self.v.check(t, BROKEN[n])
            self.assertEqual(verdict, "fail", n)
            self.assertTrue(note, n)

    def test_timeout_and_syntax_error(self):
        t = Task("x", meta={"tests": "assert f()==1"})
        self.assertEqual(self.v.check(t, "```python\ndef f():\n    while True: pass\n```")[0], "fail")
        self.assertEqual(self.v.check(t, "```python\ndef f(:\n```")[0], "fail")

    def test_plain_code_without_fence(self):
        t = Task("x", meta={"tests": "assert f()==1"})
        self.assertEqual(self.v.check(t, "def f():\n    return 1")[0], "pass")


class SecretIsolationTest(unittest.TestCase):
    def test_model_code_cannot_see_environment_secrets(self):
        import os
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-secret"
        try:
            t = Task("x", meta={"tests": "assert leak() is None"})
            code = "import os\ndef leak():\n    return os.environ.get('ANTHROPIC_API_KEY')"
            self.assertEqual(CodeVerifier(timeout=3).check(t, code)[0], "pass")
            r = CodeVerifier(timeout=3).score_tests(code, "assert leak() is None")
            self.assertEqual((r["passed"], r["total"]), (1, 1))
        finally:
            del os.environ["ANTHROPIC_API_KEY"]


if __name__ == "__main__":
    unittest.main()
