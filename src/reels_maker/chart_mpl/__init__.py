"""Matplotlib-backed chart frame sequences for Studio data scenes.

Renders the plot area of supported chart scenes to deterministic RGBA PNG
frames with matplotlib, then hands them to the scene graph as a ``sequence``
node. Scene copy, background, transitions and audio stay on the native
pipeline; only the plot is rasterized by matplotlib.
"""
from __future__ import annotations
