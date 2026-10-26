"""Argument parser definition for the public reels-maker CLI."""
from __future__ import annotations

import argparse
from pathlib import Path

from .paths import ROOT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reels-maker",
        description="Render manifest-driven videos in project-defined formats")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "render"):
        command = commands.add_parser(name)
        command.add_argument("project", type=Path, help="JSON manifest path")
        command.add_argument("--root", type=Path, default=ROOT, help="Asset root")
        command.add_argument("--json", action="store_true", help="Versioned JSON output")
        if name == "validate":
            command.add_argument("--syntax-only", action="store_true",
                                 help="Validate JSON schema without media or FFmpeg")
            command.add_argument("--strict-quality", action="store_true",
                                 help="Return error when editorial warnings are detected")
        else:
            command.add_argument("--output", type=Path)
            command.add_argument("--cache-dir", type=Path)
            command.add_argument("--no-cache", action="store_true")
            command.add_argument("--jobs", type=int, default=2,
                                 help="Concurrent scene encodes (default: 2)")
            command.add_argument("--title-engine", choices=("legacy", "studio"),
                                 default="legacy",
                                 help="Render title overlays with legacy cards or the shared studio scene graph")
            command.add_argument("--strict-quality", action="store_true",
                                 help="Refuse to render when editorial warnings remain")
    kinetic = commands.add_parser("kinetic-render",
        help="Render animated numbers, charts, EU graphics and photo motion from JSON")
    kinetic.add_argument("manifest", type=Path)
    kinetic.add_argument("--root", type=Path)
    kinetic.add_argument("--output", type=Path)
    kinetic.add_argument("--engine", choices=("legacy", "studio"),
                         default="legacy",
                         help="Use shared studio primitives (legacy Cairo remains default)")
    kinetic.add_argument("--cache-dir", type=Path,
                         help="Studio segment cache location")
    kinetic.add_argument("--no-cache", action="store_true",
                         help="Disable the Studio segment cache")
    kinetic.add_argument("--json", action="store_true")

    studio = commands.add_parser(
        "studio-render",
        help="Render a complete motion-design film with the shared scene engine")
    studio.add_argument("manifest", type=Path)
    studio.add_argument("--root", type=Path)
    studio.add_argument("--output", type=Path)
    studio.add_argument("--profile", choices=("preview", "review", "final",
                                              "high-motion"))
    studio.add_argument("--supersample", type=int, choices=(1, 2))
    studio.add_argument("--cache-dir", type=Path,
                        help="Override the default Studio segment cache directory")
    studio.add_argument("--no-cache", action="store_true",
                        help="Disable the Studio segment cache")
    studio.add_argument("--json", action="store_true")

    studio_qa = commands.add_parser(
        "studio-qa",
        help="Audit collisions, safe areas, typography, contrast, timing and data")
    studio_qa.add_argument("manifest", type=Path)
    studio_qa.add_argument("--root", type=Path)
    studio_qa.add_argument("--profile", choices=("preview", "review", "final",
                                                 "high-motion"))
    studio_qa.add_argument("--samples", type=int, default=6,
                           help="Geometry samples per scene (default: 6)")
    studio_qa.add_argument("--output-dir", type=Path)
    studio_qa.add_argument("--no-contact-sheet", action="store_true")
    studio_qa.add_argument("--strict", action="store_true",
                           help="Return exit code 2 when any error is reported")
    studio_qa.add_argument("--json", action="store_true")

    studio_info = commands.add_parser(
        "studio-inspect",
        help="Print resolved tokens, layouts, choreography and cue timings")
    studio_info.add_argument("manifest", type=Path)
    studio_info.add_argument("--root", type=Path)
    studio_info.add_argument("--profile", choices=("preview", "review", "final",
                                                   "high-motion"))
    studio_info.add_argument("--json", action="store_true")
    cues = commands.add_parser("cue-sheet",
        help="List exact local/global cue times including transition overlaps")
    cues.add_argument("project", type=Path)
    cues.add_argument("--output", type=Path, help="Optional JSON report destination")
    cues.add_argument("--json", action="store_true")

    audio_qc = commands.add_parser("audio-qc",
        help="Measure integrated LUFS and true peak without modifying the audio")
    audio_qc.add_argument("file", type=Path)
    audio_qc.add_argument("--reference-lufs", type=float,
                          help="Optional editorial loudness reference, not a platform standard")
    audio_qc.add_argument("--json", action="store_true")

    inspect = commands.add_parser("inspect")
    inspect.add_argument("file", type=Path)
    inspect.add_argument("--json", action="store_true")
    verify = commands.add_parser("verify",
        help="Reject incorrect exported MP4 dimensions, frames, codecs or audio")
    verify.add_argument("project", type=Path)
    verify.add_argument("--video", type=Path, required=True)
    verify.add_argument("--json", action="store_true")
    storyboard = commands.add_parser("storyboard",
        help="Extract a contact sheet from real MP4 scene frames for visual QC")
    storyboard.add_argument("project", type=Path)
    storyboard.add_argument("--video", type=Path, required=True)
    storyboard.add_argument("--output", type=Path, required=True)
    storyboard.add_argument("--columns", type=int, default=4)
    storyboard.add_argument("--root", type=Path)
    storyboard.add_argument("--profile", choices=("preview", "review", "final",
                                                    "high-motion"))
    storyboard.add_argument("--motion-strip", action="store_true",
        help="Show entry/settled/exit frames for every shot")
    storyboard.add_argument("--json", action="store_true")
    discover = commands.add_parser("catalog")
    discover.add_argument("--root", type=Path, default=ROOT)
    discover.add_argument("--brand", help="Limit media catalog to a brand slug")
    discover.add_argument("--probe", action="store_true",
                          help="Inspect each available media file (slower)")
    discover.add_argument("--limit", type=int, default=500)
    discover.add_argument("--json", action="store_true")
    site = commands.add_parser("brand-scan",
        help="Create CSS/font/logo proposal and brandbook PDF from a public website")
    site.add_argument("url", help="Public HTTP(S) website address")
    site.add_argument("--brand", required=True, help="Brand slug")
    site.add_argument("--root", type=Path, default=ROOT)
    site.add_argument("--output", type=Path, help="JSON audit destination")
    site.add_argument("--no-logo-download", action="store_true")
    site.add_argument("--no-pdf", action="store_true")
    site.add_argument("--json", action="store_true")

    brandbook = commands.add_parser("brandbook")
    brandbook.add_argument("--brand", required=True)
    brandbook.add_argument("--root", type=Path, default=ROOT)
    brandbook.add_argument("--output", type=Path)
    brandbook.add_argument("--json", action="store_true")
    plan = commands.add_parser("plan",
        help="Convert a reviewed brief into an explainable studio manifest draft; "
             "VALIDATE WITH studio-qa (studio manifests are file-optional)")
    plan.add_argument("brief", type=Path, help="Brief JSON path")
    plan.add_argument("--root", type=Path, default=ROOT,
                      help="Repository root containing brands/")
    plan.add_argument("--brand", help="Brand slug; overrides brief['brand']")
    plan.add_argument("--write-manifest", action="store_true",
                      help="Save the manifest into brands/<slug>/projects/")
    plan.add_argument("--force", action="store_true",
                      help="Overwrite an existing draft manifest")
    plan.add_argument("--json", action="store_true")
    library = commands.add_parser("library",
        help="Validate a reviewed asset-library manifest (license metadata is "
             "mandatory)")
    library.add_argument("manifest", type=Path, help="asset-library.json path")
    library.add_argument("--json", action="store_true")
    brand_init = commands.add_parser("brand-init",
        help="Scaffold a new brand directory with placeholder identity "
             "(no media, no invented content)")
    brand_init.add_argument("slug", help="lowercase brand slug")
    brand_init.add_argument("--name", required=True, help="Readable brand name")
    brand_init.add_argument("--accent", required=True,
                            help="Verified brand accent colour, #RRGGBB")
    brand_init.add_argument("--root", type=Path, default=ROOT,
                            help="Repository root containing brands/")
    brand_init.add_argument("--force", action="store_true",
                            help="Replace an existing brand directory")
    brand_init.add_argument("--json", action="store_true")
    pixabay = commands.add_parser("pixabay",
        help="Search Pixabay music/sound-effects; download only explicitly "
             "picked candidates into the brand imports/ quarantine area")
    pixabay.add_argument("query", help="Search words or a pixabay.com URL")
    pixabay.add_argument("--kind", choices=("music", "sound-effects"),
                         default="music")
    pixabay.add_argument("--root", type=Path, default=ROOT,
                         help="Repository root containing brands/")
    pixabay.add_argument("--brand", help="Brand slug for imports/ staging")
    pixabay.add_argument("--page-file", type=Path,
                         help="Parse a page saved from the browser instead of "
                              "fetching (needed when Cloudflare blocks us)")
    pixabay.add_argument("--tracks-file", type=Path,
                         help="Plain text file with cdn.pixabay.com MP3 urls "
                              "(one per line, from the browser network tab); "
                              "always works because the CDN is not blocked")
    pixabay.add_argument("--cookies", help="Cookie header, e.g. "
                                           "'cf_clearance=...; ...'")
    pixabay.add_argument("--limit", type=int, default=10,
                         help="Candidates to list before picking")
    pixabay.add_argument("--pick", help="Comma-separated candidate numbers to "
                                        "download, e.g. --pick 2,3")
    pixabay.add_argument("--all", action="store_true",
                         help="Download every listed candidate")
    pixabay.add_argument("--json", action="store_true")
    media_search = commands.add_parser(
        "media-search",
        help="Search public stock-media APIs and save ranked, unapproved candidates")
    media_search.add_argument("query", help="Search terms")
    media_search.add_argument("--provider", choices=("all", "pexels", "pixabay",
        "unsplash", "wikimedia_commons", "openverse"), default="all")
    media_search.add_argument("--kind", choices=("image", "video", "audio"),
                              default="image")
    media_search.add_argument("--limit", type=int, default=12,
                              help="Candidates requested from each provider (1..50)")
    media_search.add_argument("--aspect", type=float, default=9/16,
                              help="Target width/height used for ranking")
    media_search.add_argument("--output", type=Path,
                              help="Optional candidate report JSON path")
    media_search.add_argument("--json", action="store_true")
    media_download = commands.add_parser(
        "media-download",
        help="Download one exact-item reviewed candidate into brand imports quarantine")
    media_download.add_argument("candidate_file", type=Path,
                                help="Candidate record or media-search report JSON")
    media_download.add_argument("--provider", required=True,
        choices=("pexels", "pixabay", "unsplash", "wikimedia_commons", "openverse"))
    media_download.add_argument("--asset-id", required=True,
                                help="Exact provider asset ID from search result")
    media_download.add_argument("--rights-decision", type=Path, required=True,
                                help="Human-reviewed exact-item rights decision JSON")
    media_download.add_argument("--brand", required=True)
    media_download.add_argument("--root", type=Path, default=ROOT)
    media_download.add_argument("--target-platform", required=True)
    media_download.add_argument("--transcode", choices=("h264_mp4",))
    media_download.add_argument("--json", action="store_true")
    sfx = commands.add_parser(
        "sfx-generate",
        help="Generate deterministic procedural SFX into imports/audio quarantine")
    sfx.add_argument("--brand", required=True, help="Existing brand slug")
    sfx.add_argument("--root", type=Path, default=ROOT,
                     help="Repository root containing brands/")
    sfx.add_argument("--kind", choices=("click", "whoosh", "riser", "hit"),
                     required=True)
    sfx.add_argument("--duration", type=float, default=0.45,
                     help="Duration in seconds (0.03..3.0)")
    sfx.add_argument("--sample-rate", type=int, choices=(22050, 44100, 48000),
                     default=48000)
    sfx.add_argument("--seed", type=int, default=0)
    sfx.add_argument("--peak", type=float, default=0.20,
                     help="Linear peak amplitude (0.01..0.50)")
    sfx.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    creative_caps = commands.add_parser(
        "creative-capabilities", help="Versioned capability registry for LLM callers")
    creative_caps.add_argument("--json", action="store_true")
    creative_schema = commands.add_parser(
        "creative-schema", help="Export JSON Schema for LLM structured outputs")
    creative_schema.add_argument("--json", action="store_true")

    creative_val = commands.add_parser(
        "creative-validate", help="Validate Creative Spec v1 and perform asset/geometry QA")
    creative_val.add_argument("spec", type=Path)
    creative_val.add_argument("--root", type=Path)
    creative_val.add_argument("--semantic-only", action="store_true")
    creative_val.add_argument("--json", action="store_true")

    creative_compile = commands.add_parser(
        "creative-compile", help="Compile LLM-authored Creative Spec to executable Studio JSON")
    creative_compile.add_argument("spec", type=Path)
    creative_compile.add_argument("--root", type=Path)
    creative_compile.add_argument("--output", type=Path)
    creative_compile.add_argument("--force", action="store_true")
    creative_compile.add_argument("--strict", action="store_true",
                                  help="Reject warnings in addition to errors")
    creative_compile.add_argument("--json", action="store_true")

    creative_edit = commands.add_parser(
        "creative-edit", help="Apply JSON Patch edits to a Creative Spec without overwriting original")
    creative_edit.add_argument("spec", type=Path)
    creative_edit.add_argument("patch", type=Path)
    creative_edit.add_argument("--output", type=Path, required=True)
    creative_edit.add_argument("--force", action="store_true")
    creative_edit.add_argument("--json", action="store_true")

    creative_render = commands.add_parser(
        "creative-render", help="Compile, preflight and render Creative Spec via actual Studio engine")
    creative_render.add_argument("spec", type=Path)
    creative_render.add_argument("--root", type=Path)
    creative_render.add_argument("--output", type=Path, required=True)
    creative_render.add_argument("--storyboard", type=Path)
    creative_render.add_argument("--cache-dir", type=Path,
                                 help="Override the default Studio segment cache directory")
    creative_render.add_argument("--no-cache", action="store_true",
                                 help="Disable the Studio segment cache")
    creative_render.add_argument("--strict", action="store_true")
    creative_render.add_argument("--json", action="store_true")

    return parser
