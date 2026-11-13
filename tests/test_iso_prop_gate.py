"""Regression lock for the gate's stale-render refusal (playbook 17).

A reviewer once failed a 50-minute-old render while the code was
already fixed — wasted round. ``iso_prop_gate --audit`` must fail
fast when the builder source is newer than the PNG, before any LLM
quota is spent.
"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, "tools")

from iso_prop_gate import is_stale_render  # noqa: E402


class StaleRenderTest(unittest.TestCase):
    def test_newer_source_is_stale(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "props_x.py")
            img = os.path.join(td, "01-x.png")
            open(img, "w").write("png")
            time.sleep(0.05)
            open(src, "w").write("code")
            os.utime(src, (time.time() + 10, time.time() + 10))
            self.assertTrue(is_stale_render(src, img))

    def test_newer_render_is_fresh(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "props_x.py")
            img = os.path.join(td, "01-x.png")
            open(src, "w").write("code")
            time.sleep(0.05)
            open(img, "w").write("png")
            os.utime(img, (time.time() + 10, time.time() + 10))
            self.assertFalse(is_stale_render(src, img))

    def test_missing_files_fail_open(self):
        self.assertFalse(is_stale_render("/no/such/src.py",
                                        "/no/such/img.png"))


if __name__ == "__main__":
    unittest.main()
