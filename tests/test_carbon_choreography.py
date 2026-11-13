"""Pure planning contracts and native graph integration for Carbon choreography."""
import copy
import unittest
from types import SimpleNamespace as NS
from reels_maker.motionkit.carbon_choreography import (
    adaptive_duration,accent_indices,prepare_project,bridge_transform,apply_project,_roles,_bridge,
)


class CarbonChoreographyPolicyTests(unittest.TestCase):
    def test_distance_and_scale_change_increase_duration(self):
        duration=lambda d,a,b:adaptive_duration(d,a,b,720,60,3)
        self.assertLess(duration(10,1,1),duration(400,1,1))
        self.assertLess(duration(10,1,1),duration(10,1,2))
        self.assertAlmostEqual(duration(400,1,1)*60,round(duration(400,1,1)*60))

    def test_expressive_motion_and_available_hold(self):
        p=adaptive_duration(200,1,1,720,30,3)
        e=adaptive_duration(200,1,1,720,30,3,"expressive")
        self.assertGreaterEqual(e,p)
        with self.assertRaises(ValueError): adaptive_duration(400,1,1,720,30,.1)

    def test_invalid_numeric_inputs(self):
        for args in [(float("nan"),1,1,720,30,3),(1,0,1,720,30,3),(1,1,1,720,True,3)]:
            with self.assertRaises(ValueError): adaptive_duration(*args)

    def test_accent_budget_respects_locks_and_disabled_scenes(self):
        scenes=[{"creative_intent":"proof","carbon_motion":None},
            {"creative_intent":"proof","carbon_motion":{},"carbon_lock":True},
            {"creative_intent":"opening","carbon_motion":{}},
            {"creative_intent":"proof","carbon_motion":{}}]
        self.assertEqual(accent_indices(scenes,1),[3])
        scenes.append({"carbon_motion":{"mode":"expressive"}})
        self.assertEqual(accent_indices(scenes,1),[])

    def test_preparation_does_not_mutate_caller_scene_objects(self):
        scenes=[{"carbon_motion":{"mode":"productive"},"creative_intent":"proof"}]
        original=copy.deepcopy(scenes)
        project=NS(scenes=scenes,export={"carbon_director":True})
        prepare_project(project)
        self.assertEqual(scenes,original)
        self.assertEqual(project.scenes[0]["carbon_motion"]["mode"],"expressive")

    def test_shared_cache_dependency_tracks_target_changes(self):
        scenes=[{"carbon_shared":{"same":"visual"}},
                {"carbon_shared":{"same":"visual"},"headline":"A"}]
        project=NS(scenes=scenes,export={})
        prepare_project(project); first=project.scenes[0]["_carbon_shared_next"]
        prepare_project(project)
        self.assertEqual(first,project.scenes[0]["_carbon_shared_next"])
        project.scenes[1]["headline"]="B";prepare_project(project)
        self.assertNotEqual(first,project.scenes[0]["_carbon_shared_next"])

    def test_duplicate_shared_role_bindings_are_rejected(self):
        with self.assertRaises(ValueError):
            prepare_project(NS(scenes=[{"carbon_shared":{"one":"visual","two":"visual"}}],export={}))

    def test_bridge_transform_matches_destination_with_custom_anchor(self):
        base=(100,200,180,280);goal=(300,400,460,560);anchor=(100,200)
        scale,dx,dy=bridge_transform(base,goal,anchor)
        actual=(anchor[0]+scale*(base[0]-anchor[0])+dx,
                anchor[1]+scale*(base[1]-anchor[1])+dy,
                anchor[0]+scale*(base[2]-anchor[0])+dx,
                anchor[1]+scale*(base[3]-anchor[1])+dy)
        self.assertEqual(actual,goal)

    def test_bridge_rejects_distortion(self):
        with self.assertRaises(ValueError):bridge_transform((0,0,10,10),(0,0,20,30))

    def test_no_advanced_config_keeps_existing_built_objects(self):
        built=[object()]
        self.assertIs(apply_project(NS(scenes=[{}]),built),built)


class CarbonChoreographyNativeTests(unittest.TestCase):
    def fixture(self,node,scene=None):
        scene=scene or {"carbon_motion":{"mode":"productive"}}
        return NS(nodes=[node],elements={node.role:node},meta={},scene=scene,duration=4.,
                  _subtree_settles={},_settled_samples={})

    def project(self):
        return NS(width=720,height=1280,fps=30,
                  tokens=NS(safe_pixels=lambda w,h:(50,100,100)))

    def test_explicit_multikey_phases_preserve_hold(self):
        from reels_maker.core.scene_graph import Node
        from reels_maker.motionkit.keyframes import Keyframe,Track
        node=Node("rect","hero",props={"x":100,"y":200,"w":80,"h":80})
        node.tracks["opacity"]=Track([Keyframe(0,0),Keyframe(.4,1),Keyframe(2,1),Keyframe(3,0)])
        item=self.fixture(node); hold=node.tracks["opacity"].keys[2]
        _roles(item,{"roles":{"hero":{"segments":{"opacity":[{"index":1,"phase":"entrance"},{"index":3,"phase":"exit"}]}}}},self.project())
        self.assertEqual(node.tracks["opacity"].keys[2],hold)
        self.assertNotEqual(node.tracks["opacity"].keys[1].params,node.tracks["opacity"].keys[3].params)

    def test_root_path_uses_offset_axis_tracks(self):
        from reels_maker.core.scene_graph import Node
        node=Node("rect","hero",props={"x":100,"y":200,"w":80,"h":80})
        _roles(self.fixture(node),{"roles":{"hero":{"path":{"to":[.2,.1],"at":1,"duration":.8}}}},self.project())
        self.assertLess(node.tracks["dx"].end,node.tracks["dy"].end)
        self.assertLess(node.tracks["dx"].start,node.tracks["dy"].start)
        self.assertEqual(node.sample(2).dx,144)
        self.assertEqual(node.sample(2).dy,128)

    def test_native_shared_geometry_matches_at_encoded_boundary(self):
        from reels_maker.core.scene_graph import Node
        a=Node("rect","visual",props={"x":100,"y":200,"w":80,"h":80,"fill":(20,90,200)})
        b=Node("rect","visual",props={"x":300,"y":400,"w":160,"h":160,"fill":(20,90,200)})
        left,right=self.fixture(a),self.fixture(b)
        _bridge(left,right,"visual","visual",self.project(),.7)
        end=left.meta["carbon_shared"][0]["end"]
        for x,y in zip(a.sample(end).world_bounds(),b.sample(0).world_bounds()):
            self.assertAlmostEqual(x,y)
        self.assertEqual(b.sample(0).opacity,1)

    def test_failure_does_not_mutate_original_graph(self):
        from reels_maker.core.scene_graph import Node
        node=Node("rect","visual",props={"x":100,"y":200,"w":80,"h":80})
        scene={"carbon_motion":{},"carbon_choreography":{"roles":{"missing":{}}}}
        original=self.fixture(node,scene);project=self.project();project.scenes=[scene]
        with self.assertRaises(ValueError):apply_project(project,[original])
        self.assertEqual(node.tracks,{})
        self.assertEqual(original.meta,{})

    def test_normal_studio_build_runs_the_hook(self):
        import json,tempfile
        from pathlib import Path
        from reels_maker.studio import load_studio
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"test.json"
            path.write_text(json.dumps({"name":"carbon-advanced-test","video":{"width":360,"height":640,"fps":30},
                "scenes":[{"composition":"statement","headline":"CARBON","duration":4,
                           "carbon_choreography":{"attention_limit":3}}]}),encoding="utf-8")
            project=load_studio(path,root=folder)
            self.assertIn("carbon_concurrency",project.build()[0].meta)


if __name__=="__main__":unittest.main()
