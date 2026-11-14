import unittest

from reels_maker.creative.llm.contracts import (
    CreativeContractError,
    validate_brief,
    validate_concepts,
    validate_revision_patch,
    validate_scene_program,
    validate_visual_critique,
)
from reels_maker.creative.llm.orchestrator import run_creative_loop


class _AcceptingModel:
    def __init__(self):
        self.calls = []
        self.scene_context = None

    def generate_json(self, *, role, context):
        self.calls.append(role)
        if role == "concepts":
            common = {"visual_metaphor": "A roof becomes a power circuit",
                      "hero_moment": "The home lights up", "story_beats": ["need", "proof"],
                      "transition_logic": "follow the energy path", "risks": []}
            return [{**common, "id": "a", "title": "Energy path", "mechanism": "visual journey"},
                    {**common, "id": "b", "title": "Before and after", "mechanism": "contrast"}]
        if role == "select_concept":
            return {"concept_id": "a"}
        if role == "art_direction":
            return {
                "visual_thesis": "One signal emerges from deliberate stillness.",
                "selected_recipe_id": "R02",
                "principle_ids": ["P04", "P03"],
                "rejected_anti_patterns": ["A01", "A08"],
                "hierarchy": ["single focal headline", "supporting line"],
                "typography": "One display face, restrained contrast.",
                "image_relationship": "No image assets; typography carries the demonstration.",
                "motion_grammar": ["one mask reveal", "settled readable hold"],
                "rhythm": "Short reveal, long hold, clean cut.",
                "scenes": [{"id": "one", "viewer_task": "read the idea",
                            "focal_point": "the headline", "visual_change": "mask reveal",
                            "hold": "hold until the scene ends",
                            "transition_reason": "let the statement resolve",
                            "evidence_ids": []}],
                "risks": [],
            }
        if role == "scene_program":
            self.scene_context = context
            return {"creative_spec": {"creative_schema_version": 1, "name": "test",
                    "mode": "studio", "style": "editorial-premium",
                    "video": {"width": 360, "height": 640, "fps": 24},
                    "shots": [{"id": "one", "headline": "A CLEAR IDEA", "duration": 2.8}]},
                    "decisions": [{"id": "one", "layout": "statement",
                                    "typography_motion": "mask-rise"}]}
        if role == "critic":
            return {"evidence_hash": context["evidence"]["sha256"],
                    "observed_modalities": ["image"],
                    "verdict": "accept", "issues": []}
        raise AssertionError(role)


class _RevisingModel(_AcceptingModel):
    def __init__(self):
        super().__init__()
        self.critic_calls = 0

    def generate_json(self, *, role, context):
        if role == "critic":
            self.calls.append(role)
            self.critic_calls += 1
            if self.critic_calls == 1:
                return {"evidence_hash": context["evidence"]["sha256"],
                        "observed_modalities": ["image"], "verdict": "revise",
                        "issues": [{"scene_id": "one", "timecode": "0.8s",
                                    "observed": "Headline arrives before the eye can settle.",
                                    "impact": "The idea reads as rushed.",
                                    "revision": "Shorten the wording without changing its claim."}]}
            return {"evidence_hash": context["evidence"]["sha256"],
                    "observed_modalities": ["image"], "verdict": "accept", "issues": []}
        if role == "revise":
            self.calls.append(role)
            return {"revision_patch": [{"op": "replace",
                    "path": "/shots/@one/headline", "value": "ONE IDEA"}]}
        return super().generate_json(role=role, context=context)


class CreativeLLMContractTests(unittest.TestCase):
    def test_brief_requires_provenance_for_facts_and_explicit_media_rights(self):
        brief = {
            "name": "Demo", "audience": "Homeowners", "goal": "Explain value",
            "promise": "Clear evidence", "platform": "reels", "brand": {},
            "restrictions": [], "facts": [{"id": "f1", "claim": "12 kW", "source": "report"}],
            "media": [{"id": "m1", "path": "assets/roof.png", "rights_status": "unknown"}],
        }
        self.assertEqual(validate_brief(brief)["facts"][0]["source"], "report")
        brief["facts"][0].pop("source")
        with self.assertRaises(CreativeContractError):
            validate_brief(brief)

    def test_concepts_must_differ_by_story_mechanism(self):
        base = {"title": "Idea", "visual_metaphor": "A house as a system",
                "hero_moment": "Light travels through the home", "story_beats": ["show", "prove"],
                "transition_logic": "match cut", "risks": []}
        concepts = [{**base, "id": "a", "mechanism": "before-after"},
                    {**base, "id": "b", "mechanism": "before-after"}]
        with self.assertRaises(CreativeContractError):
            validate_concepts(concepts)

    def test_visual_critique_must_reference_render_evidence(self):
        with self.assertRaises(CreativeContractError):
            validate_visual_critique({"evidence_hash": "old", "verdict": "accept",
                                      "observed_modalities": ["image"], "issues": []},
                                     evidence_hash="current")

    def test_visual_critique_must_declare_a_received_visual_modality(self):
        with self.assertRaises(CreativeContractError):
            validate_visual_critique({"evidence_hash": "a" * 64, "verdict": "accept",
                                      "observed_modalities": ["audio"], "issues": []},
                                     evidence_hash="a" * 64)

    def test_revision_cannot_change_global_or_fact_fields(self):
        with self.assertRaises(CreativeContractError):
            validate_revision_patch([{"op": "replace", "path": "/facts/f1/claim", "value": "new"}])

    def test_scene_program_requires_exact_stable_scene_ids(self):
        program = {"creative_spec": {"shots": [{"id": "one"}]},
                   "decisions": [{"id": "one"}]}
        self.assertEqual(validate_scene_program(program, scene_ids={"one"}), program)
        reordered = {"creative_spec": {"shots": [{"id": "two"}, {"id": "one"}]},
                     "decisions": [{"id": "two"}, {"id": "one"}]}
        with self.assertRaises(CreativeContractError):
            validate_scene_program(reordered, scene_ids=["one", "two"])
        with self.assertRaises(CreativeContractError):
            validate_scene_program(program, scene_ids={"two"})

    def test_art_direction_cannot_cite_unknown_brief_evidence(self):
        from reels_maker.creative.llm.contracts import validate_art_direction
        from reels_maker.creative.reference_library import load_reference_library
        brief = {"facts": [], "media": []}
        art = _AcceptingModel().generate_json(role="art_direction", context={})
        art["scenes"][0]["evidence_ids"] = ["invented"]
        guidance = load_reference_library()
        with self.assertRaises(CreativeContractError):
            validate_art_direction(art, brief=brief, reference_guidance=guidance)

    def test_bounded_loop_returns_human_review_pending_not_fake_approval(self):
        brief = {"name": "Demo", "audience": "People", "goal": "Explain", "promise": "Clear",
                 "platform": "reels", "brand": {}, "restrictions": [], "facts": [], "media": []}
        model = _AcceptingModel()
        result = run_creative_loop(
            brief, model=model,
            render_evidence=lambda _program, _round: {"sha256": "a" * 64,
                                                       "render_id": "fixture-only",
                                                       "host_observation_required": True},
            hard_qa=lambda _spec, _decisions: {"ok": True},
        )
        self.assertEqual(result["status"], "needs_human_review")
        self.assertEqual(result["human_approval"], "pending")
        self.assertEqual(model.calls, ["concepts", "select_concept", "art_direction",
                                       "scene_program", "critic"])
        self.assertIn("art_direction", model.scene_context)

    def test_bounded_loop_revises_only_scene_patch_then_rerenders(self):
        brief = {"name": "Demo", "audience": "People", "goal": "Explain", "promise": "Clear",
                 "platform": "reels", "brand": {}, "restrictions": [], "facts": [], "media": []}
        model = _RevisingModel()
        rendered_rounds = []

        def evidence(program, round_index):
            rendered_rounds.append((round_index, program["creative_spec"]["shots"][0]["headline"]))
            digest = "a" * 64 if round_index == 0 else "b" * 64
            return {"sha256": digest, "render_id": f"synthetic-{round_index}",
                    "host_observation_required": True}

        result = run_creative_loop(
            brief, model=model, render_evidence=evidence,
            hard_qa=lambda _spec, _decisions: {"ok": True}, max_rounds=1)
        self.assertEqual(rendered_rounds, [(0, "A CLEAR IDEA"), (1, "ONE IDEA")])
        self.assertEqual(result["status"], "needs_human_review")
        self.assertEqual(result["best_candidate"]["program"]["creative_spec"]["shots"][0]["headline"],
                         "ONE IDEA")
        self.assertEqual(result["stop_reason"], "critic_has_no_open_issues")
        revision = next(item for item in result["run_ledger"] if item["stage"] == "revision")
        self.assertEqual(revision["patch"]["stable_scene_ids"], ["one"])
        self.assertEqual(result["human_approval"], "pending")

    def test_revision_cannot_replace_the_whole_program_or_reorder_scenes(self):
        from reels_maker.creative.llm.revision import apply_scene_revision_patch
        program = {
            "creative_spec": {"creative_schema_version": 1, "name": "test",
                "mode": "studio", "shots": [
                    {"id": "one", "headline": "A CLEAR IDEA", "duration": 2.8}]},
            "decisions": [{"id": "one", "layout": "statement",
                           "typography_motion": "mask-rise"}],
        }
        original = {key: value.copy() for key, value in program.items()}
        for path in ("/facts/@fact1/claim", "/shots/@missing/headline",
                     "/shots/@one/headline/text", "/shots/@one/brand"):
            with self.assertRaises(CreativeContractError):
                apply_scene_revision_patch(program, [{"op": "replace", "path": path,
                                                       "value": "forbidden"}])
        self.assertEqual(program, original)


if __name__ == "__main__":
    unittest.main()
