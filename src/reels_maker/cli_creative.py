"""Creative Spec CLI command handlers."""
from __future__ import annotations

import json
from pathlib import Path

from .spec import ProjectError
from .cli_common import _emit


def handle_creative(args) -> int:
    import tempfile
    from .creative.registry import capabilities
    from .creative.spec import validate_creative_spec
    from .creative.compiler import compile_creative_spec
    from .creative.quality import audit_creative_spec
    from .creative.edit import edit_creative_spec
    if args.command=="creative-capabilities":
        result=capabilities()
    elif args.command=="creative-schema":
        from .creative.schema import creative_json_schema
        result={"json_schema":creative_json_schema()}
    else:
        spec=json.loads(args.spec.read_text(encoding="utf-8"))
        if args.command=="creative-edit":
            patches=json.loads(args.patch.read_text(encoding="utf-8"))
            revised,changes=edit_creative_spec(spec,patches)
            destination=args.output.resolve()
            if destination==args.spec.resolve():
                raise ProjectError("creative-edit must write a new versioned file")
            if not spec.get("brand") and destination.parent!=args.spec.parent.resolve():
                raise ProjectError(
                    "Unbranded Creative Spec revisions must stay beside source assets")
            if destination.exists() and not args.force:
                raise ProjectError(f"Output exists: {destination} (use --force)")
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(
                json.dumps(revised,ensure_ascii=False,indent=2)+"\n",
                encoding="utf-8")
            result={"spec":str(destination),"changes":changes}
        elif args.command=="creative-validate" and args.semantic_only:
            result={"validation":validate_creative_spec(spec),
                    "assets_checked":False}
        else:
            manifest,plan=compile_creative_spec(
                spec,source_dir=args.spec.parent,root=args.root,
                check_assets=True)
            qa=audit_creative_spec(spec,manifest,
                source_dir=args.spec.parent,root=args.root)
            if not qa["ok"] or (getattr(args,"strict",False)
                                 and qa["warnings"]):
                _emit({"status":"error","ok":False,"qa":qa,"plan":plan,
                       "error":{"type":"CreativeQualityError",
                                "message":"Creative Spec has unresolved QA issues"}},
                      error=True)
                return 2
            if args.command=="creative-validate":
                result={"validation":validate_creative_spec(spec),
                        "qa":qa,"plan":plan,"assets_checked":True}
            elif args.command=="creative-compile":
                destination=(args.output or args.spec.with_suffix(".studio.json")).resolve()
                if destination==args.spec.resolve():
                    raise ProjectError("Compiler output must not overwrite Creative Spec")
                if not spec.get("brand") and destination.parent!=args.spec.parent.resolve():
                    raise ProjectError(
                        "Unbranded Studio manifests must stay beside source assets")
                if destination.exists() and not args.force:
                    raise ProjectError(f"Output exists: {destination} (use --force)")
                report_path=destination.with_suffix(".creative-report.json")
                if report_path.exists() and not args.force:
                    raise ProjectError(f"Report exists: {report_path} (use --force)")
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_text(
                    json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",
                    encoding="utf-8")
                report_path.write_text(
                    json.dumps({"plan":plan,"qa":qa},ensure_ascii=False,indent=2)+"\n",
                    encoding="utf-8")
                result={"manifest":str(destination),"report":str(report_path),
                        "plan":plan,"qa":qa}
            else:
                from .studio import load_studio
                from .renderers.backend import BackendOptions, render_with_backend
                from .storyboard import make_studio_storyboard
                # Keep temporary manifest beside spec, because the Studio
                # asset resolver intentionally scopes local assets to it.
                with tempfile.NamedTemporaryFile(
                        mode="w",suffix=".json",prefix=".creative-studio-",
                        dir=args.spec.parent,delete=False,encoding="utf-8") as tmp:
                    path=Path(tmp.name)
                    tmp.write(json.dumps(manifest,ensure_ascii=False)+"\n")
                try:
                    project=load_studio(path,root=args.root)
                    rendered=render_with_backend(
                        "studio", project,
                        BackendOptions(
                            output=args.output, supersample=1,
                            cache_dir=args.cache_dir,
                            cache=not args.no_cache))
                    sheet=None
                    if args.storyboard:
                        sheet=make_studio_storyboard(
                            project,Path(rendered["output"]),
                            args.storyboard,columns=4,motion_strip=True)
                    result={"render":rendered,"plan":plan,"qa":qa,
                            "storyboard":sheet}
                finally:
                    path.unlink(missing_ok=True)
    _emit({"status":"ok","ok":True,**result})
    return 0
