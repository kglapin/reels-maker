"""Reproducible raster media for the editorial rotation integration demo.

Uses existing repository-owned example raster cards: no stock API keys or
unreliable external downloads are needed to test the motion renderer.
These cards are integration fixtures, not a claim of stock photography.
"""
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"examples"/"assets"
OUT.mkdir(parents=True,exist_ok=True)
SOURCES=[
    ROOT/"archives/asta-energy/intermediates/subsidy_ad/card_01.png",
    ROOT/"archives/asta-energy/intermediates/subsidy_ad/card_04.png",
    ROOT/"archives/asta-energy/intermediates/subsidy_ad/card_07.png",
]
for idx,source in enumerate(SOURCES,1):
    if not source.is_file():
        raise FileNotFoundError(source)
    with Image.open(source) as src:
        frame=ImageOps.fit(src.convert("RGB"),(720,820),
                           method=Image.Resampling.LANCZOS,
                           centering=(.5,.45))
        frame=ImageEnhance.Contrast(frame).enhance(1.03)
        frame.save(OUT/f"rotation-{idx:02d}.jpg",quality=88,optimize=True)
    print(OUT/f"rotation-{idx:02d}.jpg")
