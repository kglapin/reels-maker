"""Unit tests for the LLM judge ensemble merge (no network calls)."""
import unittest

from tools.iso_prop_critic_llm import merge_verdicts


def _report(verdict="pass", score=9, issues=None):
    return {"verdict": verdict, "score": score,
            "issues": issues or [], "summary": verdict}


class MergeVerdictsTest(unittest.TestCase):
    def test_all_pass(self):
        out = merge_verdicts("img.png", [
            ("nvidia", _report("pass", 9)),
            ("nvidia-direct", _report("pass", 8)),
        ])
        self.assertEqual(out["verdict"], "pass")
        self.assertEqual(out["score"], 8)
        self.assertEqual(out["issues"], [])

    def test_one_fail_fails_ensemble(self):
        out = merge_verdicts("img.png", [
            ("nvidia", _report("pass", 9)),
            ("nvidia-direct", _report(
                "fail", 5, [{"severity": "major", "area": "top",
                             "what": "pipe floats", "fix": "attach"}])),
        ])
        self.assertEqual(out["verdict"], "fail")
        self.assertEqual(out["score"], 5)
        self.assertEqual(len(out["issues"]), 1)
        self.assertEqual(out["issues"][0]["judge"], "nvidia-direct")
        self.assertIn("nvidia-direct", out["summary"])

    def test_judge_error_is_fail_closed(self):
        out = merge_verdicts("img.png", [
            ("nvidia", _report("pass", 9)),
            ("gemini", {"verdict": "error", "summary": "503"}),
        ])
        self.assertEqual(out["verdict"], "fail")
        self.assertIn("gemini", out["summary"])

    def test_single_report_passthrough_shape(self):
        out = merge_verdicts("img.png", [("nvidia", _report("pass", 7))])
        self.assertEqual(out["verdict"], "pass")
        self.assertEqual(out["judges"]["nvidia"]["score"], 7)


if __name__ == "__main__":
    unittest.main()
