# PDF brandbook preview

The system can generate a two-page, printable PDF directly from
`brands/<slug>/brand.json` without copying styling rules into another file.

Install the optional dependency only when a PDF is needed:

```sh
python -m pip install -e ".[pdf]"
reels-maker brandbook --brand asta-energy --json
```

The PDF is saved by default as `renders/<slug>/brandbook.pdf`, which is ignored
by Git. Change the path with `--output`. The CLI prints JSON containing
`output`, `brand`, `pages` and `logo_included`.

The generated PDF includes color swatches with HEX values, typography guidance,
logo on a configurable contrast background, a 9:16 frame / safe-area diagram,
animation guidelines and a short verification checklist.

For ASTA Energy, the preferred Open Sans font will be used when installed;
otherwise the PDF embeds the available fallback. The source `BRAND.md`
contains longer editorial guidance for humans and agents.

The PDF generator does not run during video rendering; imports are lazy,
so the main CLI and all FFmpeg commands remain usable without ReportLab.
