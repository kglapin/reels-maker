"""Offline HTML/CSS brand discovery, PDF preview, CLI and SSRF regressions."""
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reels_maker.brand_scan import (
    MAX_CSS, MAX_HTML, MAX_LOGO, WebsiteScanError,
    _fetch, _safe_url, analyze_site, download_logo_candidates, suggested_brand,
)
from reels_maker.brandbook import make_brandbook
from reels_maker.cli import main


HTML = b"""<!DOCTYPE html><html><head>
<meta property="og:site_name" content="Demo Energy">
<meta name="theme-color" content="#47A013">
<link rel="stylesheet" href="/style.css">
<script type="application/ld+json">{"@type":"Organization",
"name":"Demo Energy","logo":"https://demo.example/assets/logo.svg"}</script>
</head><body><header><img class="site-logo" src="/assets/logo.png"
alt="Logo Demo Energy"></header><h1>Clean energy</h1></body></html>"""
CSS = b""":root { --brand-primary: #47a013; --surface: #ffffff; --ink: #14221a; }
body { font-family: 'Open Sans', sans-serif; color: #14221a; }
h1 { font-family: 'Open Sans', sans-serif; color: var(--brand-primary); }
@font-face { font-family: 'Open Sans'; src: url('/fonts/open.woff2'); }
"""


def fake_fetch(url, *, limit, timeout=7):
    if url == "https://demo.example/":
        assert limit == MAX_HTML
        return url, HTML, "text/html; charset=utf-8"
    if url == "https://demo.example/style.css":
        assert limit == MAX_CSS
        return url, CSS, "text/css"
    if url.endswith("logo.png"):
        assert limit == MAX_LOGO
        return url, b"\x89PNG\r\n\x1a\n" + b"FAKE-PNG-DATA", "image/png"
    if url.endswith("logo.svg"):
        assert limit == MAX_LOGO
        return url, b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml"
    raise AssertionError("Unexpected fetch: " + url)


class ScanTests(unittest.TestCase):
    def test_finds_colors_font_and_logo(self):
        report = analyze_site("https://demo.example/", fetch=fake_fetch)
        self.assertEqual(report["name"], "Demo Energy")
        self.assertEqual(report["palette"]["primary"], "#47A013")
        self.assertEqual(report["typography"]["primary"], "Open Sans")
        self.assertEqual(report["logos"][0]["format"], "svg")
        self.assertEqual(report["logos"][0]["confidence"], "high")
        self.assertEqual(suggested_brand(report, "demo")["branding"]["accent"], "#47A013")

    def test_logo_import_is_quarantined_to_proposals(self):
        report = analyze_site("https://demo.example/", fetch=fake_fetch)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "imports" / "assets"
            assets = download_logo_candidates(report, target, fetch=fake_fetch)
            self.assertTrue(assets)
            self.assertTrue(all(Path(a["path"]).is_file() for a in assets))
            self.assertFalse((Path(folder) / "brand.json").exists())

    def test_pdf_from_detected_identity(self):
        report = analyze_site("https://demo.example/", fetch=fake_fetch)
        with tempfile.TemporaryDirectory() as folder:
            pdf = make_brandbook(report, Path(folder) / "preview.pdf", draft=True)
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
            self.assertGreater(pdf.stat().st_size, 2000)

    def test_cli_scans_without_touching_accepted_brand(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            brand = root / "brands" / "demo"
            brand.mkdir(parents=True)
            original = '{"id":"demo","name":"Approved branding"}'
            (brand / "brand.json").write_text(original)
            with patch("reels_maker.brand_scan._fetch", side_effect=fake_fetch):
                code = main(["brand-scan", "https://demo.example/", "--brand", "demo",
                             "--root", str(root), "--no-logo-download", "--json"])
            self.assertEqual(code, 0)
            self.assertEqual((brand / "brand.json").read_text(), original)
            report_path = brand / "imports" / "website-report.json"
            self.assertTrue(report_path.is_file())
            self.assertTrue((root / "renders/demo/brandbook-proposal.pdf").is_file())
            saved = json.loads(report_path.read_text())
            self.assertEqual(saved["suggested_brand"]["source"]["status"], "unreviewed")

    def test_url_safety_rejects_credentials_file_and_nonstandard_port(self):
        for url in ("file:///etc/passwd", "https://u:p@demo.example/",
                    "http://localhost:8080", "https://demo.example:8443"):
            with self.subTest(url=url):
                with self.assertRaises(WebsiteScanError):
                    _safe_url(url)

    def test_private_dns_rejected_before_network_request(self):
        with patch("reels_maker.brand_scan.socket.getaddrinfo",
                   return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "",
                                  ("127.0.0.1", 443))]):
            with self.assertRaisesRegex(WebsiteScanError, "non-public"):
                _fetch("https://demo.example/", limit=MAX_HTML)

    def test_third_party_stylesheets_are_not_fetched(self):
        page = b'<html><head><link rel="stylesheet" href="https://evil.example/a.css">' \
               b'<meta name="theme-color" content="#47A013"></head></html>'
        def fake(url, *, limit):
            self.assertEqual(url, "https://demo.example/")
            return url, page, "text/html"
        report = analyze_site("https://demo.example/", fetch=fake)
        self.assertTrue(any("Skipped external CSS" in warning
                            for warning in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
