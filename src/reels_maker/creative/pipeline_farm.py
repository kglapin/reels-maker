"""Render farm batch planning and execution."""
from __future__ import annotations

from pathlib import Path

def plan_render_farm_batch(
    jobs: list[dict],
    *,
    gpu_hourly_cost_usd: float = 0.65,
    cpu_hourly_cost_usd: float = 0.12,
    budget_usd: float = 5.0,
) -> dict:
    """Schedule batch renders across GPU/CPU workers with cost estimation and brand-cache grouping (MD-605)."""
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("jobs must be a non-empty list")
    if budget_usd <= 0:
        raise ValueError("budget_usd must be positive")
    # Group jobs by (brand, style) to maximize warm per-scene segment cache hits
    ordered = sorted(jobs, key=lambda j: (str(j.get("brand", "")), str(j.get("style", "")), str(j.get("id", ""))))
    scheduled = []
    total_cost = 0.0
    seen_groups: set[tuple[str, str]] = set()
    for job in ordered:
        jid = str(job.get("id", ""))
        dur = float(job.get("duration_s", 15.0))
        use_gpu = bool(job.get("gpu_preferred", dur >= 20.0))
        group = (str(job.get("brand", "")), str(job.get("style", "")))
        warm_cache = group in seen_groups
        seen_groups.add(group)
        est_seconds = (dur * 0.45 if use_gpu else dur * 1.4) * (0.45 if warm_cache else 1.0)
        rate = gpu_hourly_cost_usd if use_gpu else cpu_hourly_cost_usd
        cost = (est_seconds / 3600.0) * rate
        total_cost += cost
        scheduled.append({
            "job_id": jid,
            "worker_tier": "gpu" if use_gpu else "cpu",
            "warm_brand_cache": warm_cache,
            "estimated_seconds": round(est_seconds, 2),
            "estimated_cost_usd": round(cost, 5),
        })
    if total_cost > budget_usd:
        raise ValueError(f"Batch estimated cost ${total_cost:.4f} exceeds budget ${budget_usd:.2f}")
    return {
        "ok": True,
        "job_count": len(scheduled),
        "total_estimated_cost_usd": round(total_cost, 5),
        "budget_usd": float(budget_usd),
        "schedule": scheduled,
    }

def detect_hardware_h264_encoder() -> str:
    """Probe FFmpeg for available GPU/hardware H.264 encoders, falling back to libx264 (MD-605)."""
    import subprocess

    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        out = proc.stdout or ""
        for hw in ("h264_nvenc", "h264_videotoolbox", "h264_vaapi"):
            if hw in out:
                return hw
    except Exception:
        pass
    return "libx264"

def execute_render_farm_batch(
    projects: list,
    output_dir: str | Path,
    *,
    budget_usd: float = 5.0,
) -> dict:
    """Schedule and execute a batch of StudioProject renders with shared warm segment caching (MD-605)."""
    from ..renderers.studio import probe_output, render_studio

    if not projects:
        raise ValueError("projects must not be empty")
    out_root = Path(output_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    cache_dir = out_root / ".segment-cache"
    jobs_spec = [
        {
            "id": p.name,
            "brand": p.brand or "default",
            "style": p.style,
            "duration_s": p.timeline().duration,
        }
        for p in projects
    ]
    plan = plan_render_farm_batch(jobs_spec, budget_usd=budget_usd)
    hw_encoder = detect_hardware_h264_encoder()
    by_id = {p.name: p for p in projects}
    completed = []
    for item in plan["schedule"]:
        proj = by_id[item["job_id"]]
        dest = out_root / f"{proj.name}.mp4"
        # Share segment cache across jobs in the same (brand, style) group
        from dataclasses import replace as _replace
        shared_proj = _replace(proj, name=f"{proj.brand or 'default'}-{proj.style}")
        rep = render_studio(shared_proj, output=dest, cache_dir=cache_dir, supersample=1)
        probed = probe_output(dest)
        completed.append({
            **item,
            "output_mp4": str(dest),
            "cache_hits": rep["cache_hits"],
            "cache_misses": rep["cache_misses"],
            "render_seconds": rep["render_seconds"],
            "frames": probed["frames"],
            "export_status": rep["export_quality"]["status"],
        })
    return {
        "ok": all(c["export_status"] == "pass" for c in completed),
        "hardware_encoder_detected": hw_encoder,
        "cache_dir": str(cache_dir),
        "plan": plan,
        "completed_jobs": completed,
    }
