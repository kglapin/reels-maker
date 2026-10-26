"""Contract tests for the stable legacy/Studio render dispatch boundary."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from reels_maker.ffmpeg import RenderError
from reels_maker.renderers.backend import (
    BackendOptions, get_backend, render_with_backend,
)
from reels_maker.spec import Project


class RenderBackendContractTests(unittest.TestCase):
    def test_backend_registry_is_explicit(self):
        self.assertEqual(get_backend("legacy").name, "legacy")
        self.assertEqual(get_backend("studio").name, "studio")
        with self.assertRaisesRegex(RenderError, "Unknown render backend"):
            get_backend("guess")

    def test_legacy_adapter_preserves_existing_report_and_options(self):
        project = Project(
            name="contract", width=360, height=640, fps=20,
            scenes=[{"file": "input.mp4", "duration": 1}],
            music=None, branding={}, output="output.mp4",
        )
        report = {"ok": True, "status": "ok", "legacy_field": "preserved"}
        with patch("reels_maker.renderer.render", return_value=report) as render:
            result = render_with_backend(
                "legacy", project,
                BackendOptions(
                    output="delivery.mp4", cache_dir="cache", cache=False,
                    jobs=3, title_engine="studio"))
        render.assert_called_once_with(
            project, output=Path("delivery.mp4"), cache_dir=Path("cache"),
            cache=False, jobs=3, title_engine="studio")
        self.assertIs(result, report)

    def test_legacy_defaults_to_two_workers_without_changing_function_api(self):
        project = Project(
            name="contract", width=360, height=640, fps=20,
            scenes=[{"file": "input.mp4", "duration": 1}],
            music=None, branding={}, output="output.mp4",
        )
        with patch("reels_maker.renderer.render", return_value={"ok": True}) as render:
            render_with_backend("legacy", project)
        self.assertEqual(render.call_args.kwargs["jobs"], 2)
        self.assertEqual(render.call_args.kwargs["title_engine"], "legacy")

    def test_studio_adapter_preserves_existing_report_and_options(self):
        project = object()
        report = {"ok": True, "status": "ok", "studio_field": "preserved"}
        progress = lambda event: None
        with patch("reels_maker.renderers.studio.render_studio",
                   return_value=report) as render:
            result = render_with_backend(
                "studio", project,
                BackendOptions(
                    output="delivery.mp4", profile="preview", supersample=1,
                    cache_dir="cache", cache=False, progress=progress))
        render.assert_called_once_with(
            project, output="delivery.mp4", profile="preview", supersample=1,
            cache_dir="cache", cache=False, progress=progress)
        self.assertIs(result, report)

    def test_engine_specific_options_fail_before_backend_execution(self):
        with self.assertRaisesRegex(RenderError, "require the Studio backend"):
            render_with_backend("legacy", object(), BackendOptions(profile="preview"))
        with self.assertRaisesRegex(RenderError, "belong to the classic backend"):
            render_with_backend("studio", object(), BackendOptions(jobs=2))


if __name__ == "__main__":
    unittest.main()
