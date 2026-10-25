"""Live capability registry exposed to LLM clients.

Only capabilities backed by the current renderer are advertised as available.
Planned techniques are never passed off as renderable effects.
"""
from __future__ import annotations

from ..design.styles import STYLE_SYSTEMS
from ..motionkit.presets import PRESETS
from ..renderers.transition_engine import EFFECTS
from ..motionkit.editorial_rotation import FAMILIES as ROTATION_FAMILIES
from ..assets.provider_client import MONTHLY_LIMITS, POLICIES as PROVIDER_POLICIES
from ..icon_library import (LICENSES as ICON_LICENSES, SEMANTIC_ROLES as ICON_ROLES,
                            STYLES as ICON_STYLES, VERSIONS as ICON_VERSIONS)

SCHEMA_VERSION = 2

# Actual renderer implementations, not aspirational prose names.
CAMERA_LAYOUTS = ("photo-above", "photo-left", "offset", "diagonal")
CAMERA_TEXT_MOTIONS = ("fade", "slide-up", "mask-rise", "scale-focus")
STUDIO_COMPOSITIONS = (
    "statement", "stack-center", "split-editorial", "full-bleed-type",
    "spotlight", "quote", "amount", "stats", "bars", "line-chart",
    "checklist", "cta", "photo-carousel", "photo-marquee",
)
PHOTO_CAROUSEL_DIRECTIONS = ("horizontal", "vertical")
CAMERA_SHOT_LIMIT = 6


def _provider_policy(provider: str) -> dict:
    policy = PROVIDER_POLICIES[provider]
    result = {
        "local_rate_limit": {"requests": policy.limit,
                             "window_seconds": policy.window_seconds,
                             "scope": "process"},
        "search_cache_ttl_seconds": policy.cache_ttl,
    }
    if provider in MONTHLY_LIMITS:
        limit, window = MONTHLY_LIMITS[provider]
        result["local_monthly_quota"] = {"requests": limit, "window_seconds": window,
                                         "scope": "process"}
    return result


class CapabilityRegistry:
    """Public, versioned description of capabilities backed by this install.

    Status values are deliberately conservative: ``implemented`` means the
    code path exists, ``partial`` means an operator or optional dependency is
    needed, and ``unsupported`` means no implementation is advertised.
    """

    schema_version = SCHEMA_VERSION

    def describe(self) -> dict:
        """Return a fresh JSON-serializable snapshot of current capabilities."""
        return {
            "schema_version": self.schema_version,
            "creative_spec_version": 1,
            "status": "ok",
            "modes": {
                "studio": {
                    "status": "implemented",
                    "compositions": list(STUDIO_COMPOSITIONS),
                    "photo_carousel_directions": list(PHOTO_CAROUSEL_DIRECTIONS),
                    "typography_presets": sorted(PRESETS),
                    "transitions": sorted(EFFECTS),
                    "editorial_rotations": list(ROTATION_FAMILIES),
                    "photo_required": False,
                },
                "camera_canvas": {
                    "status": "implemented",
                    "layouts": list(CAMERA_LAYOUTS),
                    "typography_motions": list(CAMERA_TEXT_MOTIONS),
                    "camera_fields": [
                        "x", "y", "angle", "zoom", "move_duration",
                        "reveal_delay", "reveal_duration",
                    ],
                    "photo_required": True,
                    "max_shots": CAMERA_SHOT_LIMIT,
                    "world_limit_pixels": 32_000_000,
                },
            },
            "styles": sorted(STYLE_SYSTEMS),
            "editing": {
                "status": "implemented",
                "format": "JSON Patch subset: add/replace/remove",
                "scope": "Creative Spec (not arbitrary source files)",
            },
            "providers": {
                "stock_media": [
                    {"name": "pexels", "media": ["image", "video"],
                     "status": "implemented", "authentication": "PEXELS_API_KEY",
                     "workflow": "official search API; show a prominent Pexels link and credit photographers when possible; search results remain candidates",
                     **_provider_policy("pexels")},
                    {"name": "unsplash", "media": ["image"],
                     "status": "implemented", "authentication": "UNSPLASH_ACCESS_KEY",
                     "workflow": "official search API; hotlink API image URLs, credit the photographer and Unsplash, explicitly track selected downloads",
                     **_provider_policy("unsplash")},
                    {"name": "pixabay", "media": ["image", "video"],
                     "status": "implemented", "authentication": "PIXABAY_API_KEY",
                     "limitations": ["API requires 24-hour caching; systematic mass downloads are prohibited.",
                                     "Show a prominent Pixabay link; permanent image hotlinking is prohibited; videos may be embedded."],
                     **_provider_policy("pixabay")},
                    {"name": "wikimedia_commons", "media": ["image"],
                     "status": "implemented", "authentication": "none in current search adapter",
                     "workflow": "item-level extmetadata; rights status remains unknown until reviewed",
                     **_provider_policy("wikimedia_commons")},
                    {"name": "openverse", "media": ["image"],
                     "status": "partial", "authentication": "OPENVERSE_ACCESS_TOKEN (OAuth bearer token; registered client required)",
                     "workflow": "requires an operator-provided OAuth access token; item-level license metadata is evidence only and rights status remains unknown until reviewed",
                     "limitations": ["OAuth client registration and token acquisition/refresh are not implemented; search is unavailable without a valid token."],
                     **_provider_policy("openverse")},
                ],
                "audio": [
                    {"name": "reels-maker-procedural", "media": ["sound-effects"],
                     "status": "partial", "authentication": "none",
                     "workflow": "deterministic procedural WAV generated only into imports/audio quarantine",
                      "limitations": ["rights_status remains unknown; generated sound still needs human editorial/right-to-use review before publication."]},
                    {"name": "wikimedia_commons", "media": ["audio"],
                     "status": "implemented", "authentication": "none",
                     "workflow": "official API returns per-file source/license metadata; acquisition requires an exact reviewed decision",
                     "limitations": ["Search metadata is evidence only; files remain rights-unknown until reviewer, attribution and platform are recorded."]},
                    {"name": "pixabay", "media": ["music", "sound-effects"],
                     "status": "partial",
                     "workflow": "operator-assisted search and explicit quarantine download",
                     "limitations": ["No public Pixabay audio API; search pages may require browser access.",
                                     "Downloaded audio remains quarantined pending human review."]},
                    {"name": "openverse", "media": ["audio"],
                     "status": "partial", "authentication": "OPENVERSE_ACCESS_TOKEN (OAuth bearer token)",
                     "workflow": "official metadata search; generic downloader can stage only an exact reviewed item in quarantine",
                     "limitations": ["OAuth client registration/token refresh is not implemented; item-level license review and platform decision required."]},
                ],
            },
            "icon_packs": [
                {"name": name, "status": "implemented",
                 "version": ICON_VERSIONS[name], "license": ICON_LICENSES[name],
                 "styles": list(ICON_STYLES[name]),
                 "semantic_roles": list(ICON_ROLES),
                 "material_symbol_variants": (name == "material_symbols"),
                 "obvious_logo_symbols_blocked": True,
                 "item_level_rights_review_required": True}
                for name in ICON_VERSIONS
            ],
            "feature_flags": {
                "creative_spec_compile": {"status": "implemented"},
                "creative_spec_edit": {"status": "implemented"},
                "typed_creative_pipeline_v1": {
                    "status": "implemented",
                    "limitations": ["Adapters preserve separate Studio and Camera Canvas manifest/render paths; no shared transform graph is implied."],
                },
                "stock_image_search": {"status": "implemented"},
                "stock_video_search": {"status": "implemented",
                                        "providers": ["pexels", "pixabay"]},
                "data_visualization": {
                    "status": "partial",
                    "limitations": [
                        "Studio has bars/donut/stat-grid, ordered bars, explicit vector line_chart, 100%-stacked bars and a stable-row-ID table with sort, row/cell highlights, cell counter transitions, pagination and table->bars shared-ID compilation.",
                        "Typed LoadedData bridges support line, bar, stacked_bar and table via compile_visualization_scene; full waterfall/Sankey/heatmap families and human mobile review remain.",
                    ],
                },
                "layout_solver_qa": {
                    "status": "implemented",
                    "limitations": ["solve_scene_layout and repair_scene_layout evaluate candidate compositions against timeline-sampled geometry/ink QA; aesthetic approval remains human-gated."],
                },
                "platform_safe_polygons": {
                    "status": "implemented",
                    "profiles": [
                        "instagram_reels", "tiktok", "youtube_shorts",
                        "linkedin_portrait", "square_feed", "landscape_hd",
                    ],
                },
                "vector_path_trim": {
                    "status": "implemented",
                    "limitations": ["Arc-length polyline/line trim (progress/trim_start) and icon state transitions are supported; arbitrary cubic-Bezier SVG morphs remain unsupported."],
                },
                "vector_line_chart": {
                    "status": "partial",
                    "limitations": [
                        "Explicitly configured line_chart scenes and typed LoadedData -> line_chart_scene / compile_visualization_scene compilation are supported; axes labels and y-domain are required.",
                    ],
                },
                "semantic_icon_suggestions": {
                    "status": "implemented",
                    "limitations": ["Finite reviewed role map; unknown concepts return no suggestions."],
                },
                "procedural_sfx_generation": {
                    "status": "partial",
                    "limitations": ["Outputs are quarantined and are not delivery-cleared."],
                },
                "licensed_asset_download": {
                    "status": "partial",
                    "limitations": [
                        "media-search and media-download expose ranked public-provider candidates and exact-item reviewed acquisition into brand imports quarantine.",
                        "Provider search results remain rights-unknown; Downloads require reviewer/date/evidence, exact source+URL, license and target-platform approval.",
                        "Unsplash local download is disabled because its API requires hotlinked image URLs; a compliant renderer path is not implemented.",
                        "Downloads stay unapproved in quarantine and never auto-register in the delivery library.",
                    ],
                },
                "audio_beat_sync": {"status": "unsupported"},
                "semantic_photo_sourcing": {"status": "unsupported"},
                "automatic_aesthetic_scoring": {"status": "unsupported"},
                "icon_svg_rasterization": {
                    "status": "partial",
                    "limitations": ["Requires the optional icons dependency and a cached icon or network access."],
                },
            },
            "limitations": [
                "No LLM network inference inside the backend; LLM supplies Creative Spec JSON.",
                "Only explicit local image paths can be compiled; images are not fabricated.",
                "Automatic aesthetic scoring and semantic photo sourcing are not implemented.",
                "Camera-canvas geometry uses authored or deterministic waypoints; "
                "subject detection, complex 3D camera moves and motion blur are not implemented.",
                "Audio-to-beat automation and per-letter type morphs are not implemented.",
                "Provider credentials are required; provider search results are not editorial approval.",
                "A provider-supplied license label and link are evidence, not a cleared usage decision.",
            ],
        }

def capabilities() -> dict:
    """Backward-compatible function returning the public registry snapshot."""
    return CapabilityRegistry().describe()
