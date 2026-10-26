"""Package convenience imports should not eagerly load unrelated engines."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ImportBoundaryTests(unittest.TestCase):
    def _run_fresh_import(self, code: str) -> str:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, env=env,
            check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()

    def test_scene_renderer_import_does_not_load_studio_pipeline(self):
        output = self._run_fresh_import(
            "from reels_maker.renderers.scene import SceneRenderer; "
            "import sys; "
            "print('reels_maker.renderers.studio' in sys.modules)"
        )
        self.assertEqual(output, "False")

    def test_component_base_import_does_not_load_scene_registry(self):
        output = self._run_fresh_import(
            "from reels_maker.components.base import SceneContext; "
            "import sys; "
            "print('reels_maker.components.scenes' in sys.modules)"
        )
        self.assertEqual(output, "False")

    def test_data_scene_import_does_not_load_scene_registry(self):
        output = self._run_fresh_import(
            "from reels_maker.components.data_scenes import build_bars; "
            "import sys; "
            "print(callable(build_bars), "
            "'reels_maker.components.scenes' in sys.modules)"
        )
        self.assertEqual(output, "True False")

    def test_public_reexports_still_resolve_on_demand(self):
        output = self._run_fresh_import(
            "from reels_maker.components import build_scene; "
            "from reels_maker.renderers import SceneRenderer, render_studio; "
            "print(all(callable(x) for x in "
            "(build_scene, SceneRenderer, render_studio)))"
        )
        self.assertEqual(output, "True")


if __name__ == "__main__":
    unittest.main()
