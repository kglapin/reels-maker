"""Synthetic DM-003/DM-004 typed-data to vector-chart integration."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.data_director import recommend_visualizations
from reels_maker.data_renderer import (
    DataRenderError, bar_chart_scene, compile_visualization_scene,
    line_chart_scene, paginate_table_scenes, sorted_table_scene,
    stacked_bars_100_scene, table_scene, table_to_bars_scenes,
)
from reels_maker.qa.report import audit_data_scene
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

    def test_bar_and_stacked_bar_compilers_and_unified_dispatcher(self):
        bar_data = LoadedData((
            {"region": "Północ", "output": Decimal("45.0")},
            {"region": "Południe", "output": Decimal("80.5")},
            {"region": "Zachód", "output": Decimal("62.0")},
        ), DataSchema((
            ColumnSpec("region", "string", "none", "reject"),
            ColumnSpec("output", "decimal", "MWh", "reject", currency="none"),
        ), "pl_PL", "none"), "bars.csv", "d" * 64, RIGHTS)
        plan = recommend_visualizations(
            bar_data, question="Który region produkuje najwięcej?",
            intent="magnitude_ranking",
        )
        scene = compile_visualization_scene(
            bar_data, plan, duration=3.0, data_order="descending"
        )
        self.assertEqual(scene["type"], "bars")
        self.assertEqual(scene["bars"][0]["suffix"], " MWh")
        built = build_scene(self.context(), scene)
        self.assertEqual(built.meta["row_ids"], ["Południe", "Zachód", "Północ"])
        self.assertEqual(audit_data_scene(built), [])

        stack_data = LoadedData((
            {"sector": "Dom", "source": "PV", "share_mwh": Decimal("60")},
            {"sector": "Dom", "source": "Sieć", "share_mwh": Decimal("40")},
            {"sector": "Firma", "source": "PV", "share_mwh": Decimal("75")},
            {"sector": "Firma", "source": "Sieć", "share_mwh": Decimal("25")},
        ), DataSchema((
            ColumnSpec("sector", "string", "none", "reject"),
            ColumnSpec("source", "string", "none", "reject"),
            ColumnSpec("share_mwh", "decimal", "MWh", "reject", currency="none"),
        ), "pl_PL", "none"), "stack.csv", "e" * 64, RIGHTS)
        stack_plan = recommend_visualizations(
            stack_data, question="Udział źródeł energii", intent="part_to_whole"
        )
        stack_scene = stacked_bars_100_scene(
            stack_data, stack_plan,
            category_column="sector", segment_column="source",
            value_column="share_mwh", duration=3.0,
        )
        self.assertEqual(stack_scene["type"], "stacked_bars_100")
        built_stack = build_scene(self.context(), stack_scene)
        self.assertEqual(audit_data_scene(built_stack), [])

    def test_sorted_table_animates_row_reorder_highlights_and_cell_counters(self):
        data = LoadedData((
            {"id": "r-1", "region": "Północ", "energy": Decimal("12.0")},
            {"id": "r-2", "region": "Południe", "energy": Decimal("38.0")},
            {"id": "r-3", "region": "Centrum", "energy": Decimal("24.0")},
        ), DataSchema((
            ColumnSpec("id", "string", "none", "reject"),
            ColumnSpec("region", "string", "none", "reject"),
            ColumnSpec("energy", "decimal", "kWh", "reject", currency="none"),
        ), "pl_PL", "none"), "sort.csv", "f" * 64, RIGHTS)
        scene = sorted_table_scene(
            data,
            row_id_column="id",
            visible_columns=["region", "energy"],
            column_widths={"region": .6, "energy": .4},
            alignments={"region": "left", "energy": "right"},
            duration=3.0,
            headline="Ranking mocy",
            sort_by="energy",
            sort_order="descending",
            highlight_rows=["r-2"],
            highlight_cells=[("r-3", "energy")],
            cell_transitions={"r-2": {"energy": {"from": 20.0, "to": 38.0, "suffix": " kWh"}}},
        )
        self.assertEqual([r["id"] for r in scene["rows"]], ["r-2", "r-3", "r-1"])
        self.assertEqual(scene["animate_from_row_ids"], ["r-1", "r-2", "r-3"])
        built = build_scene(self.context(), scene)
        table_children = [
            n for n in built.elements["table"].children if n.kind == "group"
        ]
        # r-2 moved from index 1 -> 0, so dy at t=0 is positive (starts lower)
        r2_node = table_children[0]
        self.assertEqual(r2_node.meta["stable_row_id"], "r-2")
        self.assertTrue(r2_node.meta["highlighted"])
        self.assertIn("dy", r2_node.tracks)
        self.assertGreater(r2_node.tracks["dy"].value(0.0), 0.0)
        self.assertAlmostEqual(r2_node.tracks["dy"].value(2.5), 0.0, places=3)
        # r-2 energy cell has an animated counter track
        num_cells = [c for c in r2_node.children if c.kind == "number"]
        self.assertEqual(len(num_cells), 1)
        self.assertIn("prop.value", num_cells[0].tracks)
        self.assertAlmostEqual(num_cells[0].tracks["prop.value"].value(0.0), 20.0, places=3)
        self.assertAlmostEqual(num_cells[0].tracks["prop.value"].value(2.5), 38.0, places=3)

    def test_table_pagination_and_table_to_bars_conservation(self):
        rows = tuple(
            {"id": f"id-{i:02d}", "name": f"Instalacja {i}", "kwh": Decimal(str(10 * i))}
            for i in range(1, 11)
        )
        schema = DataSchema((
            ColumnSpec("id", "string", "none", "reject"),
            ColumnSpec("name", "string", "none", "reject"),
            ColumnSpec("kwh", "decimal", "kWh", "reject", currency="none"),
        ), "pl_PL", "none")
        ten_rows = LoadedData(rows, schema, "ten.csv", "1" * 64, RIGHTS)
        pages = paginate_table_scenes(
            ten_rows,
            row_id_column="id",
            visible_columns=["name", "kwh"],
            column_widths={"name": .65, "kwh": .35},
            alignments={"name": "left", "kwh": "right"},
            duration_per_page=2.5,
            headline="Instalacje",
            page_size=6,
        )
        self.assertEqual(len(pages), 2)
        self.assertEqual(len(pages[0]["rows"]), 6)
        self.assertEqual(len(pages[1]["rows"]), 4)
        self.assertEqual(
            [r["id"] for p in pages for r in p["rows"]],
            [f"id-{i:02d}" for i in range(1, 11)],
        )

        four_rows = LoadedData(rows[:4], schema, "four.csv", "2" * 64, RIGHTS)
        tbl_scene, bar_scene = table_to_bars_scenes(
            four_rows,
            row_id_column="id",
            label_column="name",
            value_column="kwh",
            visible_columns=["name", "kwh"],
            column_widths={"name": .65, "kwh": .35},
            alignments={"name": "left", "kwh": "right"},
            headline="Transformacja tabela -> wykres",
        )
        self.assertTrue(tbl_scene["data_provenance"]["conservation_verified"])
        self.assertEqual(
            tbl_scene["data_provenance"]["shared_object_ids"],
            bar_scene["data_provenance"]["shared_object_ids"],
        )
        built_tbl = build_scene(self.context(), tbl_scene)
        built_bar = build_scene(self.context(), bar_scene)
        self.assertEqual(set(built_tbl.meta["row_ids"]), set(built_bar.meta["row_ids"]))


if __name__ == "__main__":
    unittest.main()
