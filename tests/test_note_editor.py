"""Original mobile-style note typing and selection overlay contracts."""
import json
from pathlib import Path
import tempfile
import unittest

from PIL import ImageChops

from reels_maker.qa.report import audit, audit_data_scene
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.studio import load_studio


class NoteEditorTests(unittest.TestCase):
    def project(self, root: Path, note_editor: dict):
        manifest = root / "note-demo.json"
        manifest.write_text(json.dumps({
            "name": "note-editor-demo",
            "style": "editorial-premium",
            "video": {"width": 720, "height": 1280, "fps": 30},
            "scenes": [{
                "type": "note_canvas", "duration": 7.0,
                "note_editor": note_editor,
            }],
        }, ensure_ascii=False), encoding="utf-8")
        return load_studio(manifest, root=root)

    def test_note_writes_progressively_then_highlights_measured_text(self):
        with tempfile.TemporaryDirectory(prefix="note-editor-") as temp:
            root = Path(temp)
            project = self.project(root, {
                "title": "Plan na dziś",
                "text": ("Najpierw przygotuję szkic. Potem zaznaczę ważne zdanie "
                         "i dopracuję szczegóły. Na końcu sprawdzę całość."),
                "typing_profile": "human",
                "selection": {"text": "ważne zdanie", "duration": 1.0},
                "keyboard": {},
            })
            built = project.build()
            scene = built[0]
            self.assertIn("note-page", scene.elements)
            self.assertIn("note-title", scene.elements)
            self.assertIn("note-body", scene.elements)
            self.assertIn("note-caret", scene.elements)
            self.assertIn("note-selection-0", scene.elements)
            self.assertIn("note-selection-handle-0", scene.elements)
            self.assertIn("note-keyboard", scene.elements)
            self.assertIn("note-key-space", scene.elements)
            pressed = [role for role, node in scene.elements.items()
                       if role.startswith("note-key-") and node.kind == "round"
                       and len(node.tracks["scale"].keys) > 1]
            self.assertGreater(len(pressed), 5)
            self.assertEqual(audit_data_scene(scene), [])
            qa = audit(
                project, built, project.timeline(), samples_per_scene=4,
                strict=True)
            self.assertTrue(qa["ok"])
            self.assertEqual(qa["variety"]["compositions"], {"note_canvas": 1})

            renderer = SceneRenderer(
                project.width, project.height, project.tokens, project.fonts,
                options=RenderOptions(supersample=1))
            early = renderer.render(scene, .55)
            typing = renderer.render(scene, 2.4)
            selected = renderer.render(scene, 5.4)
            self.assertIsNotNone(ImageChops.difference(early, typing).getbbox())
            self.assertIsNotNone(ImageChops.difference(typing, selected).getbbox())

    def test_selection_must_match_visible_copy(self):
        with tempfile.TemporaryDirectory(prefix="note-editor-invalid-") as temp:
            project = self.project(Path(temp), {
                "title": "Test", "text": "To jest krótka notatka.",
                "selection": {"text": "brakująca fraza"},
            })
            with self.assertRaisesRegex(ValueError, "must appear"):
                project.build()

    def test_selection_highlight_continues_across_wrapped_lines(self):
        with tempfile.TemporaryDirectory(prefix="note-editor-wrap-") as temp:
            project = self.project(Path(temp), {
                "title": "Wrap test",
                "text": ("one two three four five six seven eight nine ten "
                         "eleven twelve thirteen fourteen"),
                "width_ratio": .45,
                "body_size": 38,
                "selection": {"text": "four five six"},
            })
            scene = project.build()[0]
            highlights = [role for role in scene.elements
                          if role.startswith("note-selection-")
                          and role.removeprefix("note-selection-").isdigit()]
            self.assertGreaterEqual(len(highlights), 2)

    def test_note_rejects_content_that_would_need_unreadable_fit(self):
        with tempfile.TemporaryDirectory(prefix="note-editor-overflow-") as temp:
            project = self.project(Path(temp), {
                "title": "Za dużo treści",
                "width_ratio": .5,
                "height_ratio": .30,
                "text": "Ważne zdanie. " * 55,
            })
            with self.assertRaisesRegex(ValueError, "exceeds the visible page"):
                project.build()


if __name__ == "__main__":
    unittest.main()
