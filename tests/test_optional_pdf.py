"""Video-only CLI remains usable without optional ReportLab."""
import subprocess
import sys
import unittest
from unittest.mock import patch

from reels_maker.cli import main


class OptionalPDFDependencyTests(unittest.TestCase):
    def test_cli_import_is_independent_of_reportlab(self):
        # Importing reels_maker.cli must not import the optional PDF package.
        proc = subprocess.run(
            [sys.executable, "-c",
             "import sys, reels_maker.cli; "
             "assert 'reportlab' not in sys.modules"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
