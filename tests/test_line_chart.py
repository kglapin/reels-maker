"""Synthetic vector line-chart render contract for DM-004."""
import unittest
import tempfile
from pathlib import Path

from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.core.scene_graph import collect_qa_elements
from reels_maker.design.tokens import resolve_tokens
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.renderers.studio import probe_output, render_studio
from reels_maker.studio import StudioProject
from reels_maker.textkit.typesetter import FontBook


class LineChartTests(unittest.TestCase):
    def context(self):
        width, height, fps = 720, 1280, 30
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        fonts = FontBook()
        return SceneContext(width, height, fps, 4.0, tokens,
                            "editorial-premium", fonts, scene_index=0)

    def scene(self):
        return {
            "type": "line_chart",
            "duration": 4.0,
            "headline": "Produkcja energii",
            "x_axis_type": "date",
            "x_axis_label": "Dzień pomiaru",
            "y_axis_label": "Energia (kWh)",
            "y_domain": [0, 100],
            "points": [
                {"label": "2026-01-01", "value": 24},
                {"label": "2026-01-03", "value": 68},
                {"label": "2026-01-04", "value": 51},
            ],
        }

    def test_builds_explicit_axes_domain_and_vector_series(self):
        built = build_scene(self.context(), self.scene())
        group = built.elements["chart"]
        segments = [node for node in group.children
                    if node.role.startswith("series-segment-")]
        points = [node for node in group.children
                  if node.role.startswith("series-point-")]
        ticks = [node for node in group.children
                 if node.role.startswith("y-tick-")]
        self.assertEqual(len(segments), 2)
        self.assertEqual(len(points), 3)
        self.assertEqual(len(ticks), 5)
        self.assertEqual(built.meta["y_domain"], [0.0, 100.0])
        self.assertEqual(built.meta["x_axis_type"], "date")
        child_roles = {node.role for node in group.children}
        self.assertIn("x-axis-title", child_roles)
        self.assertIn("y-axis-title", child_roles)
        self.assertIn("line-chart-surface", child_roles)
        self.assertIn("latest-value", child_roles)
        self.assertEqual(len([role for role in child_roles
                              if role.startswith("series-core-")]), 3)
        self.assertLess(segments[0].props["x1"], segments[0].props["x2"])
        # Day 2 is absent; day 3 is two thirds across the date scale, not at a
        # categorical equal spacing inferred from the number of records.
        x0 = points[0].props["cx"]
        x1 = points[1].props["cx"]
        x2 = points[2].props["cx"]
        self.assertAlmostEqual((x1 - x0) / (x2 - x0), 2/3, places=5)
        safe = built.layout.safe
        elements = [element for root in built.at(2.0)
                    for element in collect_qa_elements(root)]
        for element in elements:
            self.assertGreaterEqual(element["bounds"][0], safe.x - 1.5,
                                    element["path"])
            self.assertLessEqual(element["bounds"][2], safe.right + 1.5,
                                 element["path"])

    def test_renders_synthetic_chart_to_a_frame(self):
        context = self.context()
        built = build_scene(context, self.scene())
        renderer = SceneRenderer(context.width, context.height, context.tokens,
                                 context.fonts,
                                 options=RenderOptions(supersample=1))
        frame = renderer.render(built, 2.0)
        self.assertEqual(frame.size, (720, 1280))
        self.assertGreater(len(frame.getcolors(720 * 1280) or []), 20)

    def test_synthetic_line_chart_renders_to_probeable_mp4(self):
        context = self.context()
        with tempfile.TemporaryDirectory(prefix="line-chart-mp4-") as temp:
            root = Path(temp)
            project = StudioProject(
                path=root / "line-chart.json", root=root,
                name="Synthetic line chart smoke", width=context.width,
                height=context.height, fps=context.fps,
                style="editorial-premium", scenes=[self.scene()], brand=None,
                brand_data={}, audio={},
                export={"codec": "libx264", "crf": 26, "preset": "ultrafast"},
                tokens=context.tokens, fonts=context.fonts, asset_manager=None)
            output = root / "line-chart.mp4"
            report = render_studio(project, output=output, supersample=1)
            metadata = probe_output(output)
            self.assertEqual(report["export_quality"]["status"], "pass")
            self.assertEqual((metadata["width"], metadata["height"], metadata["fps"]),
                             (720, 1280, "30/1"))

    def test_missing_semantics_or_unbounded_data_fail_closed(self):
        for change, message in (
            ({"x_axis_label": ""}, "x_axis_label"),
            ({"y_axis_label": ""}, "y_axis_label"),
            ({"y_domain": [10, 10]}, "must exceed"),
            ({"y_domain": [0, 50]}, "outside explicit y_domain"),
            ({"points": [{"label": "same", "value": 1},
                         {"label": "same", "value": 2}]}, "unique"),
        ):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                build_scene(self.context(), {**self.scene(), **change})

    def test_date_labels_must_be_strictly_ordered_iso_days(self):
        scene = self.scene()
        scene["points"] = list(reversed(scene["points"]))
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            build_scene(self.context(), scene)
        scene = self.scene()
        scene["points"][1]["label"] = "next week"
        with self.assertRaisesRegex(ValueError, "ISO YYYY-MM-DD"):
            build_scene(self.context(), scene)


if __name__ == "__main__":
    unittest.main()
