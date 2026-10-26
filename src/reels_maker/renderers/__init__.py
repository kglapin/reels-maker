"""Software scene renderer and delivery pipeline.

Keep package imports light: importing a low-level renderer submodule must not
load the Studio delivery pipeline. Public convenience exports remain lazy.
"""
__all__ = ["RenderOptions", "SceneRenderer", "probe_output", "render_studio"]


def __getattr__(name: str):
    if name == "studio":
        from importlib import import_module

        value = import_module(".studio", __name__)
    elif name in {"RenderOptions", "SceneRenderer"}:
        from . import scene

        value = getattr(scene, name)
    elif name in {"probe_output", "render_studio"}:
        from . import studio

        value = getattr(studio, name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
