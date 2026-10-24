"""JSON Schema for structured-output LLM integrations.

The runtime validator in spec.py is authoritative for cross-field rules,
asset scoping, supported effects and camera/scene combinations.
"""
from .registry import CAMERA_LAYOUTS, CAMERA_TEXT_MOTIONS, STUDIO_COMPOSITIONS

def creative_json_schema():
    number={"type":"number"}
    shot={
        "type":"object",
        "additionalProperties":False,
        "required":["id","headline"],
        "properties":{
            "id":{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9_-]*$","maxLength":80},
            "intent":{"type":"string","maxLength":300},
            "headline":{"type":"string","minLength":1,"maxLength":160},
            "subtitle":{"type":"string","maxLength":300},
            "kicker":{"type":"string","maxLength":300},
            "duration":{"type":"number","minimum":.5,"maximum":30},
            "asset":{"type":"string","minLength":1,"maxLength":500},
            "layout":{"type":"string","enum":["auto",*CAMERA_LAYOUTS,*STUDIO_COMPOSITIONS]},
            "composition":{"type":"string","enum":list(STUDIO_COMPOSITIONS)},
            "typography":{"type":"object","additionalProperties":False,
                "properties":{
                    "family":{"type":"string","enum":["auto",*CAMERA_TEXT_MOTIONS,
                                                         "fade-up","rise","word-cascade",
                                                         "pop-settle","slide-left","slide-right",
                                                         "reveal-right","tracking-in","none"]},
                    "duration":{"type":"number","minimum":.1,"maximum":3},
                    "delay":{"type":"number","minimum":0,"maximum":3},
                }},
            "camera":{"type":"object","additionalProperties":False,
                "properties":{
                    "x":{"type":"number","minimum":0,"maximum":16000},
                    "y":{"type":"number","minimum":0,"maximum":16000},
                    "angle":{"type":"number","minimum":-720,"maximum":720},
                    "zoom":{"type":"number","minimum":.65,"maximum":2},
                    "move_duration":{"type":"number","minimum":.05,"maximum":4},
                    "reveal_delay":{"type":"number","minimum":0,"maximum":3},
                    "reveal_duration":{"type":"number","minimum":.05,"maximum":3},
                }},
            "transition":{"type":"object","additionalProperties":False,
                "properties":{
                    "type":{"type":"string"},
                    "duration":{"type":"number","minimum":.1,"maximum":2},
                    "direction":{"type":"string","enum":["left","right","up","down"]},
                }},
            "rotation":{"type":"object"},
            "visual":{},
            "value":{},
            "chart":{"type":"object","additionalProperties":False,
                "required":["points","x_axis_label","y_axis_label","y_domain"],
                "properties":{
                    "points":{"type":"array","minItems":2,"maxItems":12,
                        "items":{"type":"object","additionalProperties":False,
                            "required":["label","value"],
                            "properties":{"label":{"type":"string","minLength":1,
                                                        "maxLength":80},
                                          "value":{"type":"number"}}}},
                    "x_axis_type":{"type":"string","enum":["category","date"]},
                    "x_axis_label":{"type":"string","minLength":1,"maxLength":80},
                    "y_axis_label":{"type":"string","minLength":1,"maxLength":80},
                    "y_domain":{"type":"array","minItems":2,"maxItems":2,
                                 "items":{"type":"number"}},
                }},
            "icon_library":{"type":"string"},
            "icon_assets":{"type":"array"},
            "allow_repeat_reason":{"type":"string","maxLength":300},
        },
    }
    return {
        "$schema":"https://json-schema.org/draft/2020-12/schema",
        "$id":"https://reels-maker.local/schemas/creative-spec-v1",
        "title":"Reels Maker Creative Spec v1",
        "description":"Deterministic LLM-facing structured intent. Validate with creative-validate before rendering.",
        "type":"object",
        "additionalProperties":False,
        "required":["creative_schema_version","name","mode","shots"],
        "properties":{
            "creative_schema_version":{"const":1},
            "name":{"type":"string","minLength":1,"maxLength":80},
            "mode":{"enum":["studio","camera_canvas"]},
            "style":{"type":"string"},
            "brand":{"type":"string","pattern":"^[a-z0-9]+(?:-[a-z0-9]+)*$"},
            "video":{"type":"object","additionalProperties":False,
                "properties":{
                    "width":{"type":"integer","minimum":180,"maximum":4096},
                    "height":{"type":"integer","minimum":180,"maximum":4096},
                    "fps":{"type":"integer","minimum":1,"maximum":120},
                }},
            "shots":{"type":"array","minItems":1,"maxItems":24,"items":shot},
            "palette":{"type":"object","additionalProperties":False,
                "properties":{k:{"type":"string","pattern":"^#[0-9a-fA-F]{6}$"}
                    for k in ("background","surface","ink","muted","accent")}},
            "seed":{"type":"integer","minimum":0,"maximum":2147483647},
            "audio":{"type":"object"},
            "creative_direction":{"type":"string","maxLength":1000},
        },
    }
