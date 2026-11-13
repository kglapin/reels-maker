"""Focused locks for corpus-gate fixes (playbook rule 18).

Each class pins one judge-proven defect structurally (no LLM quota):
the builder must emit geometry the fix claims. Failing-first per
fix; green after.
"""
import math
import sys
import unittest

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from tools.iso_layer_audit import Rec  # noqa: E402
from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402


def _paint(builder, *args, **kwargs):
    from reels_maker.iso import props_extra  # noqa: E402
    fn = getattr(props_extra, builder)
    q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
    fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE), *args, **kwargs)
    return q


class WeatherFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: anemometer cups unreadable (2px dots),
    sensor box floating with no bracket, solar panel unmounted."""

    def test_cups_are_world_sized(self):
        q = _paint("weather")
        cups = [c for c in q.calls
                if c["op"] in ("disc", "gnd")
                and 0.10 <= math.hypot(c["pts"][0][0] - 0.0,
                                       c["pts"][0][1] - 0.15) <= 0.18
                and 0.85 <= c["pts"][0][2] <= 0.91]
        self.assertGreaterEqual(
            len(cups), 3,
            "3 world-sized cups at the crossarm ends, not px dots")

    def test_sensor_box_has_bracket(self):
        q = _paint("weather")
        mounts = [c for c in q.calls
                  if c["op"] == "box"
                  and (min(p[1] for p in c["pts"]) - 0.15) <= 0.020
                  and (max(p[1] for p in c["pts"]) - 0.15) >= 0.036
                  and 0.45 <= sum(p[2] for p in c["pts"]) / 8 <= 0.62
                  and max(max(p[i] for p in c["pts"])
                          - min(p[i] for p in c["pts"])
                          for i in range(3)) <= 0.06]
        self.assertGreaterEqual(len(mounts), 1,
                                "visible bracket pole->sensor box")

    def test_panel_has_bracket(self):
        q = _paint("weather")
        mounts = [c for c in q.calls
                  if c["op"] == "box"
                  and (min(p[1] for p in c["pts"]) - 0.15) < -0.02
                  < (max(p[1] for p in c["pts"]) - 0.15)
                  and 0.64 <= sum(p[2] for p in c["pts"]) / 8 <= 0.78]
        self.assertGreaterEqual(len(mounts), 1,
                                "visible bracket pole->solar panel")


def _paint_electro(builder):
    from reels_maker.iso import props_electro  # noqa: E402
    from tools.iso_layer_audit import Rec  # noqa: E402
    from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
    fn = getattr(props_electro, builder)
    q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
    fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
    return q


class JunctionFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: gland stubs end at z=-0.10, floating
    0.025 above the plinth (~-0.125). 'Into the ground' must bury."""

    def test_stubs_bury_into_plinth(self):
        q = _paint_electro("junction_box")
        stubs = [c for c in q.calls
                 if c["op"] == "box"
                 and min(p[2] for p in c["pts"]) <= -0.135
                 and any(abs((p[0]) - gx) < 0.03
                         for p in c["pts"] for gx in (-0.09, 0.09))]
        self.assertGreaterEqual(len(stubs), 2,
                                "both gland stubs bury 0.01+ into plinth")


class WallboxFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12, superseded by round 2: the in-face
    riser box read as an arm (judge-rejected), so the cable is now
    a holster-rooted loop (line) proud of the face, ending in a
    plug head box left of the post (judge-approved, gate PASS 8).
    This locks the loop geometry, not the rejected box."""

    def test_loop_and_plug(self):
        q = _paint_electro("wallbox")
        loops = [c for c in q.calls
                 if c["op"] == "line"
                 and min(p[0] for p in c["pts"]) <= -0.15
                 and max(p[2] for p in c["pts"]) >= 0.55]
        self.assertGreaterEqual(len(loops), 1, "cable loop to plug")
        plugs = [c for c in q.calls
                 if c["op"] == "box"
                 and max(p[0] for p in c["pts"]) <= -0.10
                 and min(p[2] for p in c["pts"]) <= 0.60
                 and max(p[2] for p in c["pts"]) >= 0.68]
        self.assertGreaterEqual(len(plugs), 1,
                                "plug head left of post")


def _paint_tools(builder):
    from reels_maker.iso import props_tools  # noqa: E402
    from tools.iso_layer_audit import Rec  # noqa: E402
    from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
    fn = getattr(props_tools, builder)
    q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
    fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
    return q


def _paint_mod(modname, builder):
    import importlib as _il  # noqa: E402
    from tools.iso_layer_audit import Rec  # noqa: E402
    from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
    fn = getattr(_il.import_module(f"reels_maker.iso.{modname}"), builder)
    q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
    fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
    return q


class IconValveFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: the display plinth bleeds off the
    frame bottom (both judges). Plinth must sit fully in frame."""

    def test_plinth_fully_in_frame(self):
        import tools.iso_phantom_sheets as S  # noqa: E402
        from tools.iso_corpus_verify import _frame  # noqa: E402
        from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
        img = S.painters()["props_icons.icon-valve"][0](
            dict(DEFAULT_PALETTE)).im.convert("RGB")
        small = _frame(img, "props_icons.icon-valve")
        bg = tuple(DEFAULT_PALETTE["bg"][:3])
        bottom = [small.getpixel((x, small.height - 1 - dy))
                  for x in range(0, small.width, 8)
                  for dy in range(4)]
        self.assertTrue(all(px == bg for px in bottom),
                        "plinth fully inside the frame")

    def test_pedestal_grounds_icon(self):
        q = _paint_mod("props_icons", "icon_valve")
        ped = [c for c in q.calls
               if c["op"] == "box"
               and min(p[2] for p in c["pts"]) <= -0.10
               and max(p[2] for p in c["pts"]) >= 0.26
               and abs(sum(p[0] for p in c["pts"]) / 8) <= 0.03
               and abs(sum(p[1] for p in c["pts"]) / 8 - 0.15) <= 0.03]
        self.assertGreaterEqual(len(ped), 1,
                                "pedestal plinth->pipe, no floating icon")


class GrainAugerFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: wheels with no visible axle, tube
    meets the support post ambiguously."""

    def test_axle_spans_both_wheels(self):
        # Test paint uses cy=0.15: wheels at abs y 0.088/0.212.
        q = _paint_mod("props_farm", "grain_auger")
        axles = [c for c in q.calls
                 if c["op"] == "box"
                 and min(p[1] for p in c["pts"]) <= 0.08
                 and max(p[1] for p in c["pts"]) >= 0.22
                 and 0.10 <= sum(p[2] for p in c["pts"]) / 8 <= 0.28
                 and abs(sum(p[0] for p in c["pts"]) / 8
                         - -0.05) < 0.10]
        self.assertGreaterEqual(len(axles), 1, "axle bar wheel to wheel")

    def test_saddle_at_tube_post_crossing(self):
        q = _paint_mod("props_farm", "grain_auger")
        saddles = [c for c in q.calls
                   if c["op"] == "box"
                   and min(p[0] for p in c["pts"]) >= 0.20
                   and max(p[0] for p in c["pts"]) <= 0.36
                   and min(p[2] for p in c["pts"]) >= 0.85
                   and max(p[2] for p in c["pts"]) <= 1.10]
        self.assertGreaterEqual(len(saddles), 1,
                                "support saddle at tube crossing")


class StreetHydrantFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: waist bolts read as white floaters
    (detail law: bolts ONLY on flanges)."""

    def test_no_waist_bolts(self):
        import math  # noqa: E402
        q = _paint_mod("props_street2", "hydrant")
        bits = [c for c in q.calls
                if c["op"] == "box"
                and 0.22 <= sum(p[2] for p in c["pts"]) / 8 <= 0.28
                and 0.05 <= math.hypot(
                    sum(p[0] for p in c["pts"]) / 8,
                    sum(p[1] for p in c["pts"]) / 8 - 0.15) <= 0.13
                and max(max(p[i] for p in c["pts"])
                        - min(p[i] for p in c["pts"])
                        for i in range(3)) <= 0.03]
        self.assertEqual(bits, [], "no bolt cubes on the bare barrel")


class FastChargerFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: cable loop dips to z=0.13, reading
    as ending in mid-air. The loop must stay at plug level."""

    def test_loop_never_dips(self):
        q = _paint_mod("props_street2", "fast_charger")
        cable = [c for c in q.calls if c["op"] == "line"]
        self.assertTrue(cable, "cable lines present")
        low = [min(p[2] for p in c["pts"]) for c in cable]
        self.assertGreaterEqual(min(low), 0.15,
                                "loop stays at plug level, no dip")


class GrinderFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: rear plug fragments into a light cube
    + thin cable that read as floating bits. One plug mass, cable
    >= 0.07 wide (detail law: fewer, bigger)."""

    def test_rear_is_one_plug_mass(self):
        q = _paint_tools("grinder")
        rear_low = [c for c in q.calls
                    if c["op"] == "box"
                    and max(p[0] for p in c["pts"]) < -0.30
                    and sum(p[2] for p in c["pts"]) / 8 < 0.15]
        self.assertEqual(len(rear_low), 1,
                         "single plug mass at the cable end")

    def test_cable_column_wide(self):
        q = _paint_tools("grinder")
        cols = [c for c in q.calls
                if c["op"] == "box"
                and min(p[2] for p in c["pts"]) <= 0.12
                and max(p[2] for p in c["pts"]) >= 0.38
                and abs(sum(p[0] for p in c["pts"]) / 8
                        - -0.37) < 0.05]
        wide = [c for c in cols
                if max(p[0] for p in c["pts"])
                - min(p[0] for p in c["pts"]) >= 0.07]
        self.assertGreaterEqual(len(wide), 1, "cable column >= 0.07 wide")

    def test_trailing_cord_grounds_in_plinth(self):
        q = _paint_tools("grinder")
        cords = [c for c in q.calls
                 if c["op"] == "line" and len(c["pts"]) >= 3
                 and max(p[2] for p in c["pts"]) >= 0.40
                 and min(p[2] for p in c["pts"]) <= -0.05
                 and min(p[0] for p in c["pts"]) <= -0.55]
        self.assertGreaterEqual(len(cords), 1, "cord grip->plinth")

    def test_head_sits_low_over_disc(self):
        q = _paint_tools("grinder")
        heads = [c for c in q.calls
                 if c["op"] == "box"
                 and min(p[0] for p in c["pts"]) >= 0.05
                 and 0.18 <= min(p[2] for p in c["pts"]) <= 0.26
                 and max(p[2] for p in c["pts"]) >= 0.38]
        self.assertGreaterEqual(len(heads), 1, "head lowered toward disc")


class InverterMountTest(unittest.TestCase):
    """Corpus gate 2026-11-12: the wall unit floated on air. A slim
    wall chip stands behind it (towel-rad precedent)."""

    def test_wall_chip_behind_unit(self):
        import reels_maker.iso.world as W  # noqa: E402
        from tools.iso_layer_audit import Rec  # noqa: E402
        from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        W.inverter(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
        chips = [c for c in q.calls
                 if c["op"] == "box"
                 and min(p[1] for p in c["pts"]) <= 0.0
                 and 0.02 <= max(p[1] for p in c["pts"]) <= 0.03
                 and max(p[0] for p in c["pts"])
                 - min(p[0] for p in c["pts"]) >= 0.8
                 and max(p[2] for p in c["pts"]) >= 1.6]
        self.assertGreaterEqual(len(chips), 1, "wall chip behind unit")


class OptimizerCableFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: link cables buried behind the steel
    brackets — invisible, 'no cables'. Cables must flank the
    brackets, box-top to panel, >= 0.035 wide."""

    def test_cables_flank_brackets(self):
        # Short thick conduits, box-top straight into the panel
        # underside (relayout 2026-11-12: box lives UNDER the panel).
        q = _paint_mod("props_pv2", "optimizer")
        runs = [c for c in q.calls
                if c["op"] == "box"
                and 0.09 <= abs(sum(p[0] for p in c["pts"]) / 8) <= 0.16
                and max(p[0] for p in c["pts"])
                - min(p[0] for p in c["pts"]) >= 0.04
                and min(p[2] for p in c["pts"]) <= 0.42
                and max(p[2] for p in c["pts"]) >= 0.52]
        self.assertGreaterEqual(len(runs), 2, "two cable conduits")

    def test_terminal_strip_backs_conduits(self):
        q = _paint_mod("props_pv2", "optimizer")
        strips = [c for c in q.calls
                  if c["op"] == "box"
                  and abs(sum(p[0] for p in c["pts"]) / 8) <= 0.05
                  and max(p[1] for p in c["pts"]) <= 0.12
                  and min(p[2] for p in c["pts"]) <= 0.38
                  and max(p[2] for p in c["pts"]) >= 0.56
                  and max(p[0] for p in c["pts"])
                  - min(p[0] for p in c["pts"]) >= 0.25]
        self.assertGreaterEqual(len(strips), 1, "pale terminal strip")


class CompressorMountFixTest(unittest.TestCase):
    """Corpus gate 2026-11-12: maker plate floats off the box edge,
    grey pipe only touches the terminal box bottom exactly. Plate
    belongs ON the +X face, pipe must enter the box."""

    def _paint(self):
        import reels_maker.iso.world as W  # noqa: E402
        from tools.iso_layer_audit import Rec  # noqa: E402
        from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        W.compressor(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
        return q

    def test_plate_on_terminal_face(self):
        q = self._paint()
        plates = [c for c in q.calls
                  if c["op"] == "box"
                  and min(p[0] for p in c["pts"]) >= 0.23
                  and max(p[0] for p in c["pts"]) <= 0.26
                  and 0.09 <= sum(p[1] for p in c["pts"]) / 8 <= 0.21
                  and 0.20 <= sum(p[2] for p in c["pts"]) / 8 <= 0.34]
        self.assertGreaterEqual(len(plates), 1, "plate on the +X face")

    def test_pipe_enters_terminal_box(self):
        q = self._paint()
        pipes = [c for c in q.calls
                 if c.get("op") == "tube"
                 and abs(c.get("cx", 9) - 0.20) < 0.03
                 and abs(c.get("cy", 9) - 0.12) < 0.03
                 and c.get("z1", 0) >= 0.22]
        self.assertGreaterEqual(len(pipes), 1, "pipe enters the box")


class PVPanelFixTest(unittest.TestCase):
    """User verdict 2026-11-12: panel-single reads toy-like — thick
    white tape instead of a cell grid, dice-like clamps."""

    def _paint(self):
        q = _paint_mod("props_pv2", "panel_single")
        return q

    def test_no_tape_bars_on_cells(self):
        q = self._paint()
        bars = [c for c in q.calls
                if c["op"] == "box"
                and 0.36 <= sum(p[2] for p in c["pts"]) / 8 <= 0.42
                and (max(p[0] for p in c["pts"])
                     - min(p[0] for p in c["pts"]) > 0.015
                     or max(p[1] for p in c["pts"])
                     - min(p[1] for p in c["pts"]) > 0.015)
                and (max(p[0] for p in c["pts"])
                     - min(p[0] for p in c["pts"]) < 0.2
                     or max(p[1] for p in c["pts"])
                     - min(p[1] for p in c["pts"]) < 0.2)]
        self.assertEqual(bars, [], "no thick bars on the cell face")

    def test_hairline_cell_grid(self):
        q = self._paint()
        grid = [c for c in q.calls
                if c["op"] == "line"
                and all(0.378 <= p[2] <= 0.386 for p in c["pts"])]
        self.assertGreaterEqual(len(grid), 6, "hairline cell grid")

    def test_clamps_are_clips(self):
        q = self._paint()
        big = [c for c in q.calls
               if c["op"] == "box"
               and 0.28 <= sum(p[2] for p in c["pts"]) / 8 <= 0.42
               and max(p[0] for p in c["pts"])
               - min(p[0] for p in c["pts"]) < 0.2
               and max(p[1] for p in c["pts"])
               - min(p[1] for p in c["pts"]) < 0.2
               and max(max(p[i] for p in c["pts"])
                       - min(p[i] for p in c["pts"])
                       for i in range(3)) > 0.045]
        self.assertEqual(big, [], "no dice-sized clamps on the rim")



class WallboxCableFix2Test(unittest.TestCase):
    """Corpus gate 2026-11-12 round 2: cable must hang PROUD of the
    front face (y abs >= 0.35), rooted in holster, ending in plug."""

    def test_cable_hangs_off_face(self):
        q = _paint_electro("wallbox")
        runs = [c for c in q.calls
                if c["op"] == "line" and len(c["pts"]) >= 5]
        self.assertTrue(runs, "cable polyline present")
        holster = [c for c in runs
                   if 0.09 <= c["pts"][0][0] <= 0.14
                   and 0.20 <= c["pts"][0][1] <= 0.26
                   and 0.30 <= c["pts"][0][2] <= 0.60]
        plug = [c for c in runs
                if any(-0.23 <= p[0] <= -0.11 and 0.35 <= p[1] <= 0.47
                       and 0.50 <= p[2] <= 0.72 for p in c["pts"])]
        self.assertGreaterEqual(len(holster), 1, "rooted in holster")
        self.assertGreaterEqual(len(plug), 1, "ends in plug")


class PanelCellsTest(unittest.TestCase):
    """PV face rebuild: 18 individual gapped navy cells, never one
    blue slab with painted lines."""

    def _paint(self):
        import importlib as _il  # noqa: E402
        from tools.iso_layer_audit import Rec  # noqa: E402
        from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
        fn = getattr(_il.import_module("reels_maker.iso.props_pv2"),
                     "panel_single")
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
        return q

    def test_eighteen_cells(self):
        cells = [c for c in self._paint().calls
                 if c["op"] == "box"
                 and 0.13 <= max(p[0] for p in c["pts"])
                 - min(p[0] for p in c["pts"]) <= 0.17
                 and 0.12 <= max(p[1] for p in c["pts"])
                 - min(p[1] for p in c["pts"]) <= 0.16
                 and min(p[2] for p in c["pts"]) >= 0.30]
        self.assertGreaterEqual(len(cells), 15, "gapped cell grid")


class PanelRoofCellsTest(unittest.TestCase):
    """Plain rooftop panel: 18 gapped cells on rails on a flat roof."""

    def _paint(self):
        import importlib as _il  # noqa: E402
        from tools.iso_layer_audit import Rec  # noqa: E402
        from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
        fn = getattr(_il.import_module("reels_maker.iso.props_pv2"),
                     "panel_roof")
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
        return q

    def test_eighteen_cells(self):
        cells = [c for c in self._paint().calls
                 if c["op"] == "box"
                 and 0.13 <= max(p[0] for p in c["pts"])
                 - min(p[0] for p in c["pts"]) <= 0.17
                 and 0.12 <= max(p[1] for p in c["pts"])
                 - min(p[1] for p in c["pts"]) <= 0.16
                 and min(p[2] for p in c["pts"]) >= 0.20]
        self.assertGreaterEqual(len(cells), 15, "gapped cell grid")

    def test_roof_present(self):
        roofs = [c for c in self._paint().calls
                 if c["op"] == "box"
                 and max(p[0] for p in c["pts"])
                 - min(p[0] for p in c["pts"]) >= 1.2
                 and max(p[2] for p in c["pts"]) <= 0.12]
        self.assertGreaterEqual(len(roofs), 1, "flat roof slab")


class WelderFixTest(unittest.TestCase):
    """Gate round 2: floating visor fp, missing knobs/plugs/coil read."""

    def _paint(self):
        import importlib as _il  # noqa: E402
        from tools.iso_layer_audit import Rec  # noqa: E402
        from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
        fn = getattr(_il.import_module("reels_maker.iso.props_industry"),
                     "welding_set")
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
        return q

    def _boxes(self):
        return [c for c in self._paint().calls if c["op"] == "box"]

    def test_visor_on_mask_face(self):
        vis = [c for c in self._boxes()
               if 0.41 <= min(p[0] for p in c["pts"]) <= 0.44]
        self.assertGreaterEqual(len(vis), 1, "visor box on +X mask face")

    def test_mask_back_buried(self):
        backs = [c for c in self._boxes()
                 if 0.30 <= sum(p[0] for p in c["pts"]) / len(c["pts"]) <= 0.40
                 and min(p[1] for p in c["pts"]) <= 0.345
                 and max(p[2] for p in c["pts"]) <= 0.31]
        self.assertGreaterEqual(len(backs), 1, "mask back in hero front")

    def test_panel_knobs(self):
        kn = [c for c in self._boxes()
              if 0.12 <= sum(p[0] for p in c["pts"]) / len(c["pts"]) <= 0.22
              and 0.40 <= sum(p[2] for p in c["pts"]) / len(c["pts"]) <= 0.47]
        self.assertGreaterEqual(len(kn), 2, "2 panel knobs")


class ForkliftLightFixTest(unittest.TestCase):
    """Gate round 2: the single pale headlight was invisible. Two warm
    headlights on the visible +Y flank, above the stripe."""

    def _paint(self):
        import importlib as _il  # noqa: E402
        from tools.iso_layer_audit import Rec  # noqa: E402
        from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
        fn = getattr(_il.import_module("reels_maker.iso.props_industry"),
                     "forklift")
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
        return q

    def test_two_flank_headlights(self):
        q = self._paint()
        dots = [c for c in q.calls if c["op"] == "dot"]
        big = [c for c in dots if c["grow"] >= 3.6]
        self.assertGreaterEqual(len(big), 2, "2 visible headlights")


class InverterMountFixTest(unittest.TestCase):
    """Corpus gate round 3: short dark cubes read as debris. Tall
    conduits entering the hero face read as connected (a pipe into
    a wall needs no bracket)."""

    def _paint(self):
        import importlib as _il  # noqa: E402
        from tools.iso_layer_audit import Rec  # noqa: E402
        from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402
        fn = getattr(_il.import_module("reels_maker.iso.props_pv2"),
                     "inverter_string")
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        fn(q, 0.0, 0.15, dict(DEFAULT_PALETTE))
        return q

    def test_conduit_pipes_enter_hero(self):
        q = self._paint()
        pipes = [c for c in q.calls
                 if c["op"] == "box"
                 and 0.03 <= max(p[0] for p in c["pts"])
                 - min(p[0] for p in c["pts"]) <= 0.08
                 and min(p[1] for p in c["pts"]) <= 0.26
                 and max(p[1] for p in c["pts"]) >= 0.28
                 and min(p[2] for p in c["pts"]) <= 0.10
                 and max(p[2] for p in c["pts"]) >= 0.32]
        self.assertGreaterEqual(len(pipes), 3, "3 conduits into hero")


class SurgeAccentFixTest(unittest.TestCase):
    """House style: the surge box needs a readable amber accent."""

    def test_amber_pilot_lamp(self):
        q = _paint_mod("props_pv2", "surge_box")
        lamps = [c for c in q.calls
                 if c["op"] == "dot"
                 and c.get("grow", 0) >= 3.5
                 and 0.55 <= c["pts"][0][2] <= 0.70
                 and abs(c["pts"][0][0]) <= 0.20]
        self.assertGreaterEqual(len(lamps), 1, "amber pilot lamp")


if __name__ == "__main__":
    unittest.main()
