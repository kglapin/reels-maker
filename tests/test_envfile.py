"""The .env loader supplies provider credentials without overriding env."""
import tempfile
import unittest
from pathlib import Path

from reels_maker.envfile import load_env, parse_env


class EnvfileTests(unittest.TestCase):
    def test_parse_env_handles_quotes_comments_and_export(self):
        values = parse_env(
            "# comment\n"
            "PEXELS_API_KEY=abc123\n"
            "QUOTED=\" spaced value \"\n"
            "SINGLE='raw # not comment'\n"
            "export PIXABAY_API_KEY = k-e-y\n"
            "EMPTY=\n"
            "INLINE=value # trailing comment\n"
            "not an assignment\n"
            "=novalue\n")
        self.assertEqual(values["PEXELS_API_KEY"], "abc123")
        self.assertEqual(values["QUOTED"], " spaced value ")
        self.assertEqual(values["SINGLE"], "raw # not comment")
        self.assertEqual(values["PIXABAY_API_KEY"], "k-e-y")
        self.assertEqual(values["EMPTY"], "")
        self.assertEqual(values["INLINE"], "value")
        self.assertNotIn("not an assignment", values)
        self.assertNotIn("", values)

    def test_load_env_never_overrides_existing_variables(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / ".env"
            path.write_text("A=file-value\nB=other\n")
            environ = {"A": "env-value"}
            applied = load_env(path, environ=environ)
            self.assertEqual(environ, {"A": "env-value", "B": "other"})
            self.assertEqual(applied, ["B"])

    def test_missing_file_is_ignored(self):
        environ = {}
        applied = load_env(Path("/nonexistent/.env"), environ=environ)
        self.assertEqual((applied, environ), ([], {}))


if __name__ == "__main__":
    unittest.main()
