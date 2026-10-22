# Website brand scanner and review PDF

Install `python -m pip install -e ".[brand]"`, then run:

```bash
reels-maker brand-scan https://www.example.com --brand example --json
```

Outputs:
- `brands/example/imports/website-report.json`: proposed palette,
  fonts, logo URLs, evidence and a candidate `suggested_brand` object.
- `brands/example/imports/assets/`: downloaded logo candidates (SVG and
  supported raster images). Untrusted SVG files are **not** executed or
  rasterized.
- `renders/example/brandbook-proposal.pdf`: 2-page preview with palette,
  font hierarchy, logo preview and a 9:16 safe-area illustration.

The scanner inspects static HTML, up to six same-host CSS files, and bounded
logo candidates. It does not execute JavaScript or retrieve cookies. HTTP
destinations must resolve to public IP addresses; redirects are also checked
and connections use a pinned resolved IP.

For a proposal-only scan without logo downloads or PDF:

```bash
reels-maker brand-scan https://www.example.com --brand example --no-logo-download --no-pdf --json
```

The scanning result is **unreviewed**: computed browser styles, external
fonts, dark/light logo variants and logos embedded in inline SVG might not
be detected. Validate color roles, font licences and logo permissions
before copying approved values into production `brand.json`.

Already configured brands can generate a PDF **offline**:

```bash
python -m pip install -e ".[pdf]"
reels-maker brandbook --brand asta-energy --json
```
