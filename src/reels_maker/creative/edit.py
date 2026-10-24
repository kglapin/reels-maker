"""Atomic, version-preserving edits to Creative Spec documents.

Supports a deliberate JSON Patch subset for LLM-driven revisions. Edits never
mutate renderer source, historical versions, user media, or remote services.
"""
from __future__ import annotations
import copy
from collections.abc import Mapping
from .spec import CreativeSpecError,validate_creative_spec

class CreativeEditError(ValueError):
    pass

def _unescape(segment):
    if "~" in segment:
        import re
        if re.search(r"~(?![01])",segment):
            raise CreativeEditError("Invalid JSON Pointer escape")
    return segment.replace("~1","/").replace("~0","~")

def _resolve(container,part,path):
    if isinstance(container,list):
        if part.startswith("@"):
            matches=[i for i,s in enumerate(container) if isinstance(s,dict) and s.get("id")==part[1:]]
            if len(matches)!=1:raise CreativeEditError(f"{path}: unknown scene id")
            return matches[0]
        if part=="-":return len(container)
        if not part.isdigit():
            raise CreativeEditError(f"{path}: array index required")
        return int(part)
    if not isinstance(container,dict):
        raise CreativeEditError(f"{path}: cannot descend into scalar")
    return part

def edit_creative_spec(spec,patches):
    """Return new validated spec; leave original unchanged even on failure."""
    validate_creative_spec(spec)
    if not isinstance(patches,list) or not 1<=len(patches)<=40:
        raise CreativeEditError("patch must be a list with 1..40 operations")
    new=copy.deepcopy(spec)
    report=[]
    for number,patch in enumerate(patches):
        if not isinstance(patch,Mapping):
            raise CreativeEditError(f"patch[{number}]: expected object")
        if set(patch)-{"op","path","value"}:
            raise CreativeEditError(f"patch[{number}]: unknown keys")
        op=patch.get("op")
        if op not in ("add","replace","remove"):
            raise CreativeEditError(f"patch[{number}]: unsupported operation")
        if op in ("add","replace") and "value" not in patch:
            raise CreativeEditError(f"patch[{number}]: value required")
        path=patch.get("path")
        if not isinstance(path,str) or not path.startswith("/") or path=="/":
            raise CreativeEditError(f"patch[{number}]: absolute JSON Pointer required")
        parts=[_unescape(p) for p in path.split("/")[1:]]
        if parts[0] not in ("shots","name","style","palette","creative_direction",
                          "video","audio","mode"):
            raise CreativeEditError(f"patch[{number}]: path is not editable")
        # Must traverse known paths only; never create arbitrary nested data
        # through patch gaps.
        target=new
        for part in parts[:-1]:
            key=_resolve(target,part,path)
            missing=(key<0 or key>=len(target)) if isinstance(target,list) else key not in target
            if missing:
                raise CreativeEditError(f"{path}: intermediate node missing")
            target=target[key]
        key=_resolve(target,parts[-1],path)
        value=copy.deepcopy(patch.get("value"))
        exists=((0<=key<len(target)) if isinstance(target,list) else key in target)
        if op=="replace" and not exists:
            raise CreativeEditError(f"{path}: replacement target missing")
        if op=="remove":
            if not exists:raise CreativeEditError(f"{path}: removal target missing")
            if isinstance(target,list):target.pop(key)
            else:del target[key]
        elif isinstance(target,list):
            if op=="add":
                if key<0 or key>len(target):raise CreativeEditError(f"{path}: index out of range")
                target.insert(key,value)
            else:target[key]=value
        else:
            target[key]=value
        report.append({"operation":op,"path":path})
    try:
        summary=validate_creative_spec(new)
    except CreativeSpecError as exc:
        raise CreativeEditError(f"Patched document is invalid: {exc}") from exc
    return new,{"ok":True,"applied":report,"validation":summary}


def apply_natural_language_revision(spec: dict, instruction: str) -> tuple[dict, dict]:
    """Compile a structured natural-language revision into a shot-ID-preserving patch with cache report (MD-510)."""
    import re

    if not isinstance(instruction, str) or not instruction.strip():
        raise CreativeEditError("Revision instruction must be a non-empty string")
    text = instruction.strip()
    patches: list[dict] = []
    touched_shots: set[str] = set()

    # Pattern 1: shorten/extend/set duration of shot <id> to <seconds>s
    m_dur = re.search(
        r"(?:shorten|extend|set\s+duration\s+of|duration)\s+shot\s+([A-Za-z0-9_-]+)\s+to\s+([\d.]+)\s*s?",
        text, re.IGNORECASE,
    )
    if m_dur:
        sid, val = m_dur.group(1), float(m_dur.group(2))
        patches.append({"op": "replace", "path": f"/shots/@{sid}/duration", "value": val})
        touched_shots.add(sid)

    # Pattern 2: change/set headline of shot <id> to "<headline>"
    m_head = re.search(
        r"(?:change|set)\s+headline\s+of\s+shot\s+([A-Za-z0-9_-]+)\s+to\s+[\"']([^\"']+)[\"']",
        text, re.IGNORECASE,
    )
    if m_head:
        sid, headline = m_head.group(1), m_head.group(2)
        patches.append({"op": "replace", "path": f"/shots/@{sid}/headline", "value": headline})
        touched_shots.add(sid)

    # Pattern 3: set style to <style>
    m_style = re.search(
        r"set\s+style\s+to\s+([A-Za-z0-9_-]+)",
        text, re.IGNORECASE,
    )
    if m_style:
        patches.append({"op": "replace", "path": "/style", "value": m_style.group(1)})
        touched_shots.update(str(s.get("id")) for s in spec.get("shots", []))

    if not patches:
        raise CreativeEditError(
            "Unsupported natural-language revision; use 'set duration of shot <id> to <N>s', "
            "'change headline of shot <id> to \"...\"', or 'set style to <style>'"
        )
    updated, report = edit_creative_spec(spec, patches)
    all_ids = [str(s["id"]) for s in updated["shots"]]
    unchanged = [sid for sid in all_ids if sid not in touched_shots]
    invalidated = [sid for sid in all_ids if sid in touched_shots]
    return updated, {
        **report,
        "stable_shot_ids": all_ids,
        "cache_preserved_shot_ids": unchanged,
        "cache_invalidated_shot_ids": invalidated,
    }
