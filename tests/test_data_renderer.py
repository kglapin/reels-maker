"""Synthetic DM-003/DM-004 typed-data to vector-chart integration."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.data_director import recommend_visualizations
from reels_maker.data_renderer import DataRenderError, line_chart_scene, table_scene
from reels_maker.data_sources import (
    ColumnSpec, DataSchema, LoadedData, RightsProvenance,
)
from reels_maker.design.tokens import resolve_tokens
from reels_maker.renderers.studio import probe_output, render_studio
from reels_maker.studio import StudioProject
from reels_maker.textkit.typesetter import FontBook


RIGHTS = RightsProvenance(
    "Synthetic generated values", "synthetic test fixture", "https://example.invalid",
    "generated locally for automated test", True)


def sample(rows=None, *, source="synthetic.csv", digest="a" * 64,
           allow_missing=False):
    schema = DataSchema((
        ColumnSpec("day", "date", "none", "reject"),
        ColumnSpec("yield", "decimal", "kWh",
                   "null" if allow_missing else "reject",
                   ("NA",) if allow_missing else (), currency="none"),
    ), "en_US", "none")
    return LoadedData(tuple(rows or (
        {"day": date(2026, 1, 1), "yield": Decimal("15.5")},
        {"day": date(2026, 1, 3), "yield": Decimal("42.25")},
        {"day": date(2026, 1, 4), "yield": Decimal("51.0")},
    )), schema, source, digest, RIGHTS)


class DataRendererTests(unittest.TestCase):
    @staticmethod
    def context():
        width, height, fps = 720, 1280, 30
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        fonts = FontBook()
        return SceneContext(width, height, fps, 3.0, tokens,
                            "editorial-premium", fonts, scene_index=0)

    def test_typed_rows_preserve_order_units_and_provenance_in_chart_scene(self):
        data = sample()
        plan = recommend_visualizations(
            data, question="How did yield change?", intent="change_over_time")
        scene = line_chart_scene(data, plan, y_domain=(0, 60), duration=3.0)
        self.assertEqual(scene["type"], "line_chart")
        self.assertEqual(scene["x_axis_type"], "date")
        self.assertEqual(scene["x_axis_label"], "day")
        self.assertEqual(scene["y_axis_label"], "yield (kWh)")
        self.assertEqual([item["label"] for item in scene["points"]],
                         ["2026-01-01", "2026-01-03", "2026-01-04"])
        self.assertEqual(scene["data_provenance"]["source_sha256"], "a" * 64)
        self.assertEqual(scene["data_provenance"]["source_values_exact"],
                         ["15.5", "42.25", "51.0"])
        self.assertEqual(scene["data_provenance"]["calculation"],
                         "none; source rows plotted in supplied order")

    def test_studio_render_consumes_chart_scene_as_an_actual_mp4(self):
        data = sample()
        plan = recommend_visualizations(
            data, question="How did yield change?", intent="change_over_time")
        scene = line_chart_scene(data, plan, y_domain=(0, 60), duration=2.0)
        width, height, fps = 360, 640, 20
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        fonts = FontBook()
        with tempfile.TemporaryDirectory(prefix="typed-data-line-chart-") as temp:
            root = Path(temp)
            project = StudioProject(
                path=root / "data-chart.json", root=root, name="Synthetic data chart",
                width=width, height=height, fps=fps, style="editorial-premium",
                scenes=[scene], brand=None, brand_data={}, audio={},
                export={"codec": "libx264", "crf": 26, "preset": "ultrafast"},
                tokens=tokens, fonts=fonts, asset_manager=None)
            output = root / "data-chart.mp4"
            report = render_studio(project, output=output, supersample=1)
            metadata = probe_output(output)
        self.assertEqual(report["export_quality"]["status"], "pass")
        self.assertEqual((metadata["width"], metadata["height"], metadata["fps"]),
                         (360, 640, "20/1"))

    def test_renderer_fails_closed_on_plan_mismatch_null_dates_domains_and_precision(self):
        data = sample()
        plan = recommend_visualizations(
            data, question="How did yield change?", intent="change_over_time")
        with self.assertRaisesRegex(DataRenderError, "provenance"):
            line_chart_scene(sample(source="other.csv"), plan, y_domain=(0, 60), duration=2)
        with self.assertRaisesRegex(DataRenderError, "outside"):
            line_chart_scene(data, plan, y_domain=(0, 20), duration=2)
        with self.assertRaisesRegex(DataRenderError, "strictly increasing"):
            reversed_data = sample(rows=tuple(reversed(data.rows)))
            reversed_plan = recommend_visualizations(
                reversed_data, question="How did yield change?", intent="change_over_time")
            line_chart_scene(reversed_data, reversed_plan, y_domain=(0, 60), duration=2)
        null_data = sample(rows=({"day": date(2026, 1, 1), "yield": Decimal("15")},
                                 {"day": date(2026, 1, 2), "yield": None}),
                           allow_missing=True)
        null_plan = recommend_visualizations(
            null_data, question="How did yield change?", intent="change_over_time")
        with self.assertRaisesRegex(DataRenderError, "missing value"):
            line_chart_scene(null_data, null_plan, y_domain=(0, 60), duration=2)
        high_precision = sample(rows=(
            {"day": date(2026, 1, 1), "yield": Decimal("0.10000000000000001")},
            {"day": date(2026, 1, 2), "yield": Decimal("0.2")},
        ))
        precise_plan = recommend_visualizations(
            high_precision, question="Compare yield", intent="change_over_time")
        with self.assertRaisesRegex(DataRenderError, "represented exactly"):
            line_chart_scene(high_precision, precise_plan, y_domain=(0, 1), duration=2)

    def test_typed_rows_compile_to_stable_id_table_without_sort_or_truncation(self):
        data = LoadedData((
            {"id": "r-01", "region": "Północ", "energy": Decimal("12.50")},
            {"id": "r-02", "region": "Południe", "energy": Decimal("8.00")},
        ), DataSchema((
            ColumnSpec("id", "string", "none", "reject"),
            ColumnSpec("region", "string", "none", "reject"),
            ColumnSpec("energy", "decimal", "kWh", "reject", currency="none"),
        ), "pl_PL", "none"), "synthetic-table.csv", "b" * 64, RIGHTS)
        scene = table_scene(
            data, row_id_column="id", visible_columns=["region", "energy"],
            column_widths={"region": .65, "energy": .35},
            alignments={"region": "left", "energy": "right"},
            headline="Energia według regionu", duration=3.0)
        self.assertEqual(scene["renderer_family"], "table")
        self.assertEqual([row["id"] for row in scene["rows"]], ["r-01", "r-02"])
        self.assertEqual(scene["rows"][0]["values"]["energy"], "12.50")
        self.assertEqual(scene["columns"][1]["label"], "energy (kWh)")
        self.assertEqual(scene["data_provenance"]["source_sha256"], "b" * 64)
        built = build_scene(self.context(), scene)
        self.assertEqual(built.meta["row_ids"], ["r-01", "r-02"])
        table_nodes = built.elements["table"].children
        self.assertEqual([node.meta["stable_row_id"] for node in table_nodes
                          if node.kind == "group"], ["r-01", "r-02"])
        with tempfile.TemporaryDirectory(prefix="typed-data-table-") as temp:
            root = Path(temp)
            context = self.context()
            project = StudioProject(
                path=root / "table.json", root=root, name="Synthetic table",
                width=context.width, height=context.height, fps=context.fps,
                style="editorial-premium", scenes=[scene], brand=None,
                brand_data={}, audio={},
                export={"codec": "libx264", "crf": 26, "preset": "ultrafast"},
                tokens=context.tokens, fonts=context.fonts, asset_manager=None)
            output = root / "table.mp4"
            report = render_studio(project, output=output, supersample=1)
            metadata = probe_output(output)
            self.assertEqual(report["export_quality"]["status"], "pass")
            self.assertEqual((metadata["width"], metadata["height"]),
                             (context.width, context.height))

    def test_table_requires_explicit_layout_ids_and_complete_cell_values(self):
        data = LoadedData((
            {"id": "r1", "region": "North", "count": 5},
            {"id": "r2", "region": "South", "count": 3},
        ), DataSchema((
            ColumnSpec("id", "string", "none", "reject"),
            ColumnSpec("region", "string", "none", "reject"),
            ColumnSpec("count", "integer", "items", "reject"),
        ), "en_US", "none"), "synthetic.csv", "c" * 64, RIGHTS)
        with self.assertRaisesRegex(DataRenderError, "row ID"):
            table_scene(data, row_id_column="missing", column_widths={}, alignments={},
                        duration=2, headline="Table")
        with self.assertRaisesRegex(DataRenderError, "display limit"):
            table_scene(data, row_id_column="id", column_widths={"region": .5, "count": .5},
                        alignments={"region": "left", "count": "right"},
                        duration=2, headline="Table", max_rows=1)


if __name__ == "__main__":
    unittest.main()
