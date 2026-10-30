"""Domain command handlers for rendering, assets, QA and project management."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from .brand import brand_directory
from .asset_reviews import load_media_reviews
from .catalog import catalog
from .envfile import load_env
from .ffmpeg import RenderError, probe, require_tool
from .paths import ROOT, AssetError
from .renderer import preflight
from .spec import ProjectError, load_project
from .quality import review_project
from .cli_common import _emit


def handle_commands(args) -> int:
    if args.command == "brand-scan":
        try:
            from .brand_scan import analyze_site, download_logo_candidates, suggested_brand
            from .brandbook import make_brandbook
        except ImportError as exc:
            raise ProjectError(
                'Website brand scan requires: pip install -e ".[brand]"'
            ) from exc
        brand_dir = brand_directory(args.brand, args.root)
        imports = brand_dir / "imports"
        imports.mkdir(parents=True, exist_ok=True)
        audit = analyze_site(args.url)
        if not args.no_logo_download:
            audit["downloaded_logos"] = download_logo_candidates(
                audit, imports / "assets")
        audit["suggested_brand"] = suggested_brand(audit, args.brand)
        report = (args.output or imports / "website-report.json").resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        pdf = None
        if not args.no_pdf:
            pdf = make_brandbook(
                audit, Path(args.root).resolve() / "renders" /
                args.brand / "brandbook-proposal.pdf", draft=True)
        result = {
            "brand": args.brand, "source_url": audit["source_url"],
            "report": str(report), "brandbook_pdf": str(pdf) if pdf else None,
            "palette": audit["palette"],
            "font": audit["typography"]["primary"],
            "logo_candidates": len(audit["logos"]),
            "downloaded_logos": audit.get("downloaded_logos", []),
            "warnings": audit["warnings"], "applied": False,
        }
    elif args.command == "kinetic-render":
        if args.engine == "studio":
            from .studio import load_kinetic_studio
            from .renderers.backend import BackendOptions, render_with_backend
            project, default_output = load_kinetic_studio(
                args.manifest, root=args.root)
            result = render_with_backend(
                "studio", project,
                BackendOptions(output=args.output or default_output,
                               cache_dir=args.cache_dir,
                               cache=not args.no_cache))
            result["engine"] = "studio"
        else:
            if args.cache_dir is not None or args.no_cache:
                raise ProjectError(
                    "--cache-dir and --no-cache require --engine studio")
            from .kinetic_video import render_kinetic
            result = render_kinetic(args.manifest, root=args.root,
                                    output=args.output)
    elif args.command == "studio-render":
        from .studio import load_studio
        from .renderers.backend import BackendOptions, render_with_backend
        project = load_studio(args.manifest, root=args.root,
                              profile=args.profile)
        # Determine output directory based on status
        status = getattr(args, 'status', 'accepted')
        if status == 'in-progress':
            output_dir = project.root / "renders" / (project.brand or "studio") / "in-progress"
        else:
            output_dir = project.root / "renders" / (project.brand or "studio")
        output_dir.mkdir(parents=True, exist_ok=True)
        # Combine original output filename with status suffix
        original_output = args.output
        if original_output:
            output_path = Path(original_output).resolve()
            # If original output doesn't have status suffix, add it
            if status == 'in-progress' and not str(output_path).endswith('-in-progress.mp4'):
                output_path = output_path.parent / (output_path.stem + '-in-progress' + output_path.suffix)
        else:
            # Generate default output with status suffix
            suffix = '-in-progress' if status == 'in-progress' else ''
            name = (project.name.lower().replace(' ', '-').strip('-') or 'video')
            output_path = output_dir / f"{name}{suffix}.mp4"
        result = render_with_backend(
            "studio", project,
            BackendOptions(output=str(output_path), profile=args.profile,
                           supersample=args.supersample,
                           cache_dir=args.cache_dir,
                           cache=not args.no_cache))
        # Store the actual output path in result for downstream use
        result['output_path'] = str(output_path)
    elif args.command == "studio-inspect":
        from .studio import load_studio
        project = load_studio(args.manifest, root=args.root,
                              profile=args.profile)
        timeline = project.timeline()
        result = {**project.to_dict(),
                  "timeline": timeline.to_dict(),
                  "scenes": [scene.to_dict()
                             for scene in project.build(timeline)]}
    elif args.command == "studio-qa":
        from .studio import load_studio
        from .renderers.scene import RenderOptions, SceneRenderer
        from .qa.report import audit, contact_sheet, write_report
        project = load_studio(args.manifest, root=args.root,
                              profile=args.profile)
        timeline = project.timeline()
        built = project.build(timeline)
        renderer = SceneRenderer(project.width, project.height,
                                 project.tokens, project.fonts,
                                 options=RenderOptions(supersample=1))
        report = audit(project, built, timeline, renderer=renderer,
                       samples_per_scene=args.samples,
                       strict=args.strict)
        out_dir = (args.output_dir or (project.root / "renders" /
                   (project.brand or "studio") / "qa" /
                   project.name)).resolve()
        written = write_report(report, out_dir)
        sheet = None
        if not args.no_contact_sheet:
            sheet = contact_sheet(report, built, renderer, timeline,
                                  out_dir / "qa-contact-sheet.png")
        result = {"project": project.name, "report": written["report"],
                  "contact_sheet": str(sheet) if sheet else None,
                  "qa": report}
        if args.strict and not report["ok"]:
            _emit({"status": "error", "ok": False, **result,
                   "error": {"type": "QualityReviewRequired",
                             "message": "studio-qa reported blocking errors"}},
                  error=True)
            return 2
    elif args.command == "plan":
        from .planning import PlanningError, plan_brief
        try:
            brief = json.loads(args.brief.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectError(
                f"Cannot read brief {args.brief}: {exc}") from exc
        manifest, report = plan_brief(brief, root=args.root,
                                      brand=args.brand)
        result = {"status": "ok", "manifest": manifest, "report": report}
        if args.write_manifest:
            brand = manifest["brand"]
            projects = brand_directory(brand, args.root) / "projects"
            projects.mkdir(parents=True, exist_ok=True)
            destination = projects / f"{manifest['name']}.json"
            if destination.exists() and not args.force:
                raise ProjectError(
                    f"Draft manifest already exists: {destination} "
                    "(use --force to replace it)")
            destination.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            report_path = projects / f"{manifest['name']}.plan-report.json"
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            result["manifest_path"] = str(destination)
            result["report_path"] = str(report_path)
    elif args.command == "brandbook":
        try:
            from .brandbook import generate_brandbook
        except ImportError as exc:
            raise ProjectError("PDF support requires: pip install -e \".[pdf]\"") from exc
        result = generate_brandbook(args.brand, args.root, args.output)
    elif args.command == "catalog":
        media_root = brand_directory(args.brand, args.root) if args.brand else args.root
        reviews = (load_media_reviews(args.brand, args.root)
                   if args.brand else None)
        result = catalog(media_root, include_metadata=args.probe,
                         limit=args.limit, reviewed_assets=reviews)
        if args.brand:
            result["brand"] = args.brand
    elif args.command == "cue-sheet":
        from .cue_sheet import make_cue_sheet
        result = make_cue_sheet(load_project(args.project))
        if args.output is not None:
            location = args.output.resolve()
            location.parent.mkdir(parents=True, exist_ok=True)
            location.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            result["report"] = str(location)
    elif args.command == "audio-qc":
        from .audio_qc import analyze_audio_loudness
        result = analyze_audio_loudness(
            args.file, reference_lufs=args.reference_lufs)
    elif args.command == "inspect":
        result = {"file": str(args.file.resolve()), "metadata": probe(args.file)}
    elif args.command == "verify":
        from .export_quality import verify_export
        result = verify_export(load_project(args.project), args.video)
    elif args.command == "storyboard":
        from .storyboard import make_storyboard, make_studio_storyboard
        manifest = json.loads(args.project.read_text(encoding="utf-8"))
        is_studio = bool(manifest.get("style")) or any(
            isinstance(scene, dict) and "composition" in scene
            for scene in manifest.get("scenes", []))
        if is_studio:
            from .studio import load_studio
            project = load_studio(args.project, root=args.root,
                                  profile=args.profile)
            result = make_studio_storyboard(
                project, args.video, args.output, columns=args.columns,
                motion_strip=args.motion_strip)
        else:
            result = make_storyboard(load_project(args.project), args.video,
                                     args.output, columns=args.columns,
                                     motion_strip=args.motion_strip)
    elif args.command == "library":
        from .library import check_library
        result = {"library": check_library(args.manifest)}
    elif args.command == "brand-init":
        from .brand import init_brand
        result = {"brand_init": init_brand(
            args.slug, name=args.name, accent=args.accent,
            root=args.root, force=args.force)}
    elif args.command == "pixabay":
        from .pixabay import (fetch_search_page, download_candidates,
                              parse_tracks, parse_track_list,
                              search_page_url)
        if args.tracks_file:
            try:
                source = args.tracks_file.read_text(encoding="utf-8")
            except OSError as exc:
                raise ProjectError(
                    f"Cannot read track list {args.tracks_file}: {exc}"
                ) from exc
            tracks = parse_track_list(source)
        elif args.page_file:
            try:
                source = args.page_file.read_text(encoding="utf-8")
            except OSError as exc:
                raise ProjectError(
                    f"Cannot read saved page {args.page_file}: {exc}"
                ) from exc
            tracks = parse_tracks(source, "")[:max(1, args.limit)]
        else:
            source = fetch_search_page(args.query, args.kind,
                                       cookies=args.cookies)
            tracks = parse_tracks(
                source, search_page_url(args.query, args.kind)
            )[:max(1, args.limit)]
        result = {"query": args.query, "candidates": tracks}
        if args.all and not args.pick:
            args.pick = ",".join(str(i) for i in range(1, len(tracks) + 1))
        if args.pick:
            if not args.brand:
                raise ProjectError(
                    "Downloading requires --brand (quarantine staging "
                    "lives in brands/<slug>/imports/audio/)")
            destination = brand_directory(args.brand, args.root) / \
                "imports" / "audio"
            report = download_candidates(tracks, destination, args.pick,
                                         kind=args.kind,
                                         cookies=args.cookies)
            result["download"] = report
    elif args.command == "media-search":
        from .assets.stock_acquisition import candidate_record, search_with_fallback
        from .assets.stock_media import (
            StockAsset, search_openverse, search_pexels, search_pexels_videos,
            search_pixabay, search_pixabay_videos, search_unsplash,
            search_wikimedia_commons,
        )
        if not 1 <= args.limit <= 50:
            raise ValueError("--limit must be between 1 and 50")
        if not isinstance(args.query, str) or not args.query.strip():
            raise ValueError("Search query must contain non-whitespace text")
        if not math.isfinite(args.aspect) or args.aspect <= 0:
            raise ValueError("--aspect must be a finite positive number")
        kind_providers = {
            "image": ("pexels", "pixabay", "unsplash",
                      "wikimedia_commons", "openverse"),
            "video": ("pexels", "pixabay", "wikimedia_commons"),
            "audio": ("wikimedia_commons", "openverse"),
        }[args.kind]
        if args.provider == "all":
            providers = kind_providers
        else:
            if args.provider not in kind_providers:
                raise ValueError(
                    f"{args.kind} search is supported only by: "
                    f"{', '.join(kind_providers)}")
            providers = (args.provider,)
        orientation = ("landscape" if args.aspect > 1.2 else
                       "portrait" if args.aspect < 0.85 else "square")
        provider_limits = {"unsplash": 30, "openverse": 20}
        searches = []
        for provider in providers:
            per_page = min(args.limit, provider_limits.get(provider, 50))
            if provider == "pexels":
                fn = (lambda query, limit=per_page, orientation=orientation:
                      search_pexels_videos(query, per_page=limit,
                                           orientation=orientation)
                      if args.kind == "video" else
                      search_pexels(query, per_page=limit))
            elif provider == "pixabay":
                fn = (lambda query, limit=per_page:
                      search_pixabay_videos(query, per_page=limit)
                      if args.kind == "video" else
                      search_pixabay(query, per_page=limit))
            elif provider == "unsplash":
                fn = lambda query, limit=per_page: search_unsplash(query, per_page=limit)
            elif provider == "wikimedia_commons":
                fn = (lambda query, limit=per_page, kind=args.kind:
                      search_wikimedia_commons(query, per_page=limit,
                                               media_type=kind))
            elif provider == "openverse" and args.kind == "audio":
                from .assets.openverse_audio import search_openverse_audio

                def fn(query, limit=per_page):
                    return [StockAsset(
                        "openverse", item.asset_id, item.audio_url,
                        item.source_url, item.creator, 0, 0,
                        item.audio_url, item.source_url,
                        media_type="audio", license=item.license,
                        license_url=item.license_url,
                        attribution=item.attribution,
                        provider_url="https://openverse.org",
                        duration_seconds=item.duration_seconds)
                        for item in search_openverse_audio(query, per_page=limit)]
            else:
                fn = lambda query, limit=per_page: search_openverse(query, per_page=limit)
            fn.__name__ = provider
            searches.append(fn)
        candidates, outcomes = search_with_fallback(
            args.query, searches, aspect=args.aspect)
        records = [candidate_record(asset) for asset in candidates]
        successes = sum(item["status"] == "ok" for item in outcomes)
        search_status = ("unavailable" if successes == 0 else
                         "partial" if successes < len(outcomes) else "ok")
        result = {"query": args.query, "kind": args.kind,
                  "target_aspect": args.aspect, "providers": outcomes,
                  "candidate_count": len(records), "candidates": records,
                  "search_status": search_status,
                  "rights_status": "unknown",
                  "note": "Search results are candidates, not licensed or approved assets."}
        if args.output is not None:
            location = args.output.expanduser().resolve()
            location.parent.mkdir(parents=True, exist_ok=True)
            location.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
            result["report"] = str(location)
    elif args.command == "media-download":
        from .assets.stock_acquisition import candidate_asset, download_cleared_asset
        from .assets.stock_media import apply_reviewed_rights_decision
        try:
            candidate_doc = json.loads(args.candidate_file.read_text(encoding="utf-8"))
            decision = json.loads(args.rights_decision.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectError(f"Cannot read candidate or rights decision JSON: {exc}") from exc
        records = (candidate_doc.get("candidates") if isinstance(candidate_doc, dict)
                   and isinstance(candidate_doc.get("candidates"), list)
                   else [candidate_doc])
        matches = [record for record in records
                   if isinstance(record, dict)
                   and record.get("provider") == args.provider
                   and str(record.get("asset_id")) == args.asset_id]
        if len(matches) != 1:
            raise ProjectError("Candidate file must contain exactly one matching provider/asset ID")
        asset = candidate_asset(matches[0])
        asset = apply_reviewed_rights_decision(asset, decision)
        report = download_cleared_asset(
            asset, brand=args.brand, root=args.root,
            target_platform=args.target_platform,
            transcode_format=args.transcode)
        result = {"download": report,
                  "note": "Downloaded files remain unapproved in brands/<slug>/imports/."}
    elif args.command == "sfx-generate":
        from .audio_synthesis import SFXSpec, write_procedural_sfx
        result = {"audio": write_procedural_sfx(
            SFXSpec(args.kind, args.duration, args.sample_rate, args.seed, args.peak),
            brand=args.brand, root=args.root)}
    else:
        project = load_project(args.project)
        if args.command == "validate":
            if args.syntax_only:
                result = {"project": project.name, "scenes": len(project.scenes),
                          "duration": project.duration, "media_checked": False}
            else:
                data = preflight(project, args.root)
                result = {"project": project.name, "scenes": len(data["sources"]),
                          "duration": project.duration, "music": bool(data["music"]),
                          "voiceover": bool(data["voiceover"]),
                          "media_checked": True}
        else:
            if args.strict_quality:
                check = review_project(project, root=args.root)
                if check["warning_count"]:
                    _emit({"status": "error", "ok": False,
                           "quality": check,
                           "error": {"type": "QualityReviewRequired",
                                     "message": "Resolve design warnings before rendering"}},
                          error=True)
                    return 2
            from .renderers.backend import BackendOptions, render_with_backend
            result = render_with_backend(
                "legacy", project,
                BackendOptions(output=args.output, root=args.root,
                               cache_dir=args.cache_dir,
                               cache=not args.no_cache, jobs=args.jobs,
                               title_engine=args.title_engine))
    if args.command == "validate":
        quality = review_project(project, root=args.root)
        result["quality"] = quality
        if args.strict_quality and quality["warning_count"]:
            _emit({"status": "error", "ok": False, **result,
                   "error": {"type": "QualityReviewRequired",
                             "message": "Editorial warnings require review"}},
                  error=True)
            return 2
    _emit({"status": "ok", "ok": True, **result})
    return 0
