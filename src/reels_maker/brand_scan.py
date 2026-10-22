"""Conservative, read-only website identity discovery.

Only fetches public HTTP(S) pages, their same-host CSS and optionally logo
files. It never executes page JavaScript or modifies an accepted brand.json.
"""
from __future__ import annotations

import colorsys
import http.client
import ipaddress
import json
import re
import socket
import ssl
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit

import tinycss2

from .spec import ProjectError

MAX_HTML = 1_500_000
MAX_CSS = 800_000
MAX_LOGO = 3_000_000
COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)", re.I)
BRAND_WORDS = ("brand", "primary", "accent", "main", "theme", "corporate")
GENERIC_FONTS = {"inherit", "initial", "sans-serif", "serif", "monospace", "system-ui",
                 "Arial", "Helvetica", "Times New Roman", "unset", "revert"}


class WebsiteScanError(ValueError):
    """A website is unsafe, inaccessible or incompatible with static scanning."""


def _safe_url(url: str) -> tuple[str, str, int, str]:
    if not isinstance(url, str) or len(url) > 2048:
        raise WebsiteScanError("URL must be a string of at most 2048 characters")
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise WebsiteScanError("Only absolute http(s) website URLs are supported")
    if parts.username or parts.password:
        raise WebsiteScanError("URLs containing credentials are not allowed")
    try:
        host = parts.hostname.encode("idna").decode("ascii").lower()
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except (UnicodeError, ValueError) as exc:
        raise WebsiteScanError("Invalid website hostname or port") from exc
    if port != (443 if parts.scheme == "https" else 80):
        raise WebsiteScanError("Nonstandard website ports are not supported")
    if host in ("localhost",) or host.endswith((".local", ".internal")):
        raise WebsiteScanError("Local and internal hostnames are not allowed")
    path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
    canonical = urlunsplit((parts.scheme, host, parts.path or "/", parts.query, ""))
    return canonical, host, port, path


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, *, timeout: int):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self):
        sock = socket.create_connection((self._address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _fetch(url: str, *, limit: int, timeout: int = 7) -> tuple[str, bytes, str]:
    """Safe public-IP-pinned HTTP fetch; redirects are checked from scratch."""
    for _ in range(4):
        url, host, port, path = _safe_url(url)
        try:
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise WebsiteScanError(f"Website DNS lookup failed: {host}") from exc
        ips = {item[4][0] for item in addresses}
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise WebsiteScanError("Refusing private, loopback or non-public network address")
        ip = sorted(ips, key=lambda x: (":" in x, x))[0]
        connection = (_PinnedHTTPS(host, ip, timeout=timeout)
                      if url.startswith("https:")
                      else http.client.HTTPConnection(ip, port, timeout=timeout))
        try:
            connection.request("GET", path, headers={
                "Host": host,
                "User-Agent": "ReelsMakerBrandScanner/0.1 (+static CSS inspection)",
                "Accept": "text/html,text/css,image/svg+xml,image/png,image/webp,image/jpeg,*/*;q=0.1",
                "Accept-Encoding": "identity",
                "Connection": "close",
            })
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise WebsiteScanError("Website redirect is missing Location")
                url = urljoin(url, location)
                continue
            if not 200 <= response.status < 300:
                raise WebsiteScanError(f"Website returned HTTP {response.status}: {url}")
            content = response.read(limit + 1)
            if len(content) > limit:
                raise WebsiteScanError(f"Website resource exceeds {limit} bytes: {url}")
            return url, content, response.getheader("Content-Type", "")
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise WebsiteScanError(f"Cannot fetch website resource {url}: {exc}") from exc
        finally:
            connection.close()
    raise WebsiteScanError("Too many website redirects")


def _text(body: bytes, content_type: str) -> str:
    match = re.search(r"charset\s*=\s*([-\w]+)", content_type, re.I)
    encoding = match.group(1) if match else "utf-8"
    try:
        return body.decode(encoding, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _hex(value: str) -> str | None:
    value = value.strip()
    if value.startswith("#"):
        raw = value[1:]
        if len(raw) in (3, 4):
            raw = "".join(c * 2 for c in raw[:3])
        elif len(raw) in (6, 8):
            raw = raw[:6]
        else:
            return None
        if re.fullmatch("[0-9a-fA-F]{6}", raw):
            return "#" + raw.upper()
    if value.lower().startswith("rgb"):
        numbers = re.findall(r"[-+]?(?:\d*\.)?\d+%?", value)
        if len(numbers) >= 3:
            try:
                channel = [(round(float(x[:-1]) * 2.55) if x.endswith("%")
                            else round(float(x))) for x in numbers[:3]]
                if all(0 <= x <= 255 for x in channel):
                    return "#" + "".join(f"{x:02X}" for x in channel)
            except ValueError:
                pass
    return None


def _saturation(color: str) -> float:
    r, g, b = (int(color[x:x + 2], 16) / 255 for x in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)[2]


def _luminance(color: str) -> float:
    rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
                for x in rgb]
    return sum(a * b for a, b in zip(channels, (0.2126, 0.7152, 0.0722)))


def _srcset(value: str) -> str:
    choices = []
    for item in value.split(","):
        parts = item.strip().split()
        if not parts:
            continue
        metric = parts[1] if len(parts) > 1 else "1x"
        try:
            score = float(metric[:-1]) if metric.endswith(("w", "x")) else 1
        except ValueError:
            score = 1
        choices.append((score, parts[0]))
    return max(choices)[1] if choices else ""


class _HTMLSignals(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.stylesheets: list[str] = []
        self.inline_styles: list[str] = []
        self.font_hints: list[str] = []
        self.colors: list[tuple[str, str]] = []
        self.logos: dict[str, dict] = {}
        self.title = ""
        self.site_name = ""
        self._style = False
        self._title = False
        self._ldjson = False
        self._ldjson_text = ""
        self._header = 0

    def _logo(self, raw: str, score: int, clue: str):
        if not raw or raw.startswith(("data:", "blob:", "javascript:", "#")):
            return
        url = urljoin(self.base, raw.strip())
        try:
            _safe_url(url)
        except WebsiteScanError:
            return
        ext = urlsplit(url).path.lower().split(".")[-1]
        bonus = {"svg": 25, "png": 15, "webp": 8, "jpg": 3, "jpeg": 3}.get(ext, 0)
        candidate = self.logos.setdefault(url, {"url": url, "score": 0, "evidence": []})
        candidate["score"] = max(candidate["score"], score + bonus)
        if clue not in candidate["evidence"]:
            candidate["evidence"].append(clue)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        ident = " ".join(str(attributes.get(k, "")) for k in ("class", "id", "alt", "title")).lower()
        if tag == "header":
            self._header += 1
        if tag == "style":
            self._style = True
        if tag == "title":
            self._title = True
        if tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._ldjson = True
            self._ldjson_text = ""
        if attributes.get("style"):
            self.inline_styles.append("inline {" + attributes["style"] + "}")
        if tag == "meta":
            key = (attributes.get("name") or attributes.get("property") or "").lower()
            content = attributes.get("content", "")
            if key in ("theme-color", "msapplication-tilecolor"):
                self.colors.append((content, "meta " + key))
            elif key in ("og:site_name", "application-name"):
                self.site_name = content.strip()
            elif key in ("og:image", "twitter:image"):
                self._logo(content, 3, key + " (may be a social-preview image)")
        if tag == "link":
            rel = str(attributes.get("rel", "")).lower()
            href = attributes.get("href", "")
            if "stylesheet" in rel and href:
                self.stylesheets.append(urljoin(self.base, href))
            if "icon" in rel or "apple-touch-icon" in rel:
                self._logo(href, 8, "link rel=" + rel)
            if "fonts.googleapis.com" in href:
                for family in parse_qs(urlsplit(href).query).get("family", []):
                    self.font_hints.append(family.split(":")[0].replace("+", " "))
        if tag in ("img", "source"):
            src = (attributes.get("data-src") or attributes.get("src") or
                   _srcset(attributes.get("srcset", "")))
            score = (55 if "logo" in ident or "brand" in ident else 0)
            score += 12 if self._header else 0
            if score:
                self._logo(src, score, "HTML image: " + ident[:100])
            elif self._header:
                self._logo(src, 15, "header image (unverified logo)")
        if tag == "image" and "logo" in ident:
            self._logo(attributes.get("href") or attributes.get("xlink:href", ""),
                       40, "SVG image reference")

    def handle_endtag(self, tag):
        if tag == "style":
            self._style = False
        if tag == "title":
            self._title = False
        if tag == "header":
            self._header = max(0, self._header - 1)
        if tag == "script" and self._ldjson:
            self._ldjson = False
            try:
                self._parse_jsonld(json.loads(self._ldjson_text))
            except (ValueError, TypeError):
                pass

    def handle_data(self, data):
        if self._style:
            self.inline_styles.append(data)
        if self._title:
            self.title += data.strip()
        if self._ldjson:
            self._ldjson_text += data[:250_000]

    def _parse_jsonld(self, item):
        if isinstance(item, list):
            for sub in item[:20]:
                self._parse_jsonld(sub)
        elif isinstance(item, dict):
            if "@graph" in item:
                self._parse_jsonld(item["@graph"])
            typename = str(item.get("@type", "")).lower()
            if any(x in typename for x in ("organization", "corporation", "brand")):
                value = item.get("logo")
                if isinstance(value, dict):
                    value = value.get("url") or value.get("contentUrl")
                if isinstance(value, str):
                    self._logo(value, 85, "Organization structured data")
                if item.get("name") and not self.site_name:
                    self.site_name = str(item["name"])


def _font_name(raw: str, variables: dict[str, str]) -> str | None:
    raw = _replace_vars(raw, variables)
    names = [name.strip(" \"'") for name in raw.split(",")]
    for name in names:
        if name and name not in GENERIC_FONTS and not name.startswith(("var(", "-", "ui-")):
            return name
    return next((n for n in names if n), None)


def _replace_vars(value: str, variables: dict[str, str]) -> str:
    for _ in range(3):
        match = re.search(r"var\(\s*(--[\w-]+)(?:\s*,[^)]*)?\)", value)
        if not match:
            break
        replacement = variables.get(match.group(1), "")
        value = value[:match.start()] + replacement + value[match.end():]
    return value


def _css_signals(texts: list[str]) -> tuple[list[dict], dict, list[str]]:
    variables: dict[str, str] = {}
    rules: list[tuple[str, str, str]] = []
    font_faces: set[str] = set()
    for css in texts:
        parsed = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
        def walk(nodes):
            for item in nodes:
                if item.type == "qualified-rule":
                    selector = tinycss2.serialize(item.prelude).strip().lower()
                    declarations = tinycss2.parse_declaration_list(
                        item.content, skip_comments=True, skip_whitespace=True)
                elif item.type == "at-rule" and item.content is not None:
                    if item.lower_at_keyword in ("media", "supports", "layer"):
                        walk(tinycss2.parse_rule_list(item.content, skip_whitespace=True,
                                                      skip_comments=True))
                        continue
                    selector = "@font-face" if item.lower_at_keyword == "font-face" else "@rule"
                    declarations = tinycss2.parse_declaration_list(
                        item.content, skip_comments=True, skip_whitespace=True)
                else:
                    continue
                for d in declarations:
                    if d.type != "declaration":
                        continue
                    name = d.lower_name
                    value = tinycss2.serialize(d.value).strip()
                    rules.append((selector, name, value))
                    if name.startswith("--"):
                        variables[name] = value
                    if selector == "@font-face" and name == "font-family":
                        font_faces.add(value.strip(" \"'"))
        walk(parsed)

    colors: dict[str, dict] = {}
    font_scores = Counter()
    for selector, name, raw in rules:
        value = _replace_vars(raw, variables)
        if name in ("font-family", "font"):
            font = _font_name(value, variables)
            if font:
                priority = 5 if any(x in selector for x in ("body", "html", ":root")) else 2
                if any(x in selector for x in ("h1", "h2", "heading", ".title")):
                    priority += 5
                font_scores[font] += priority
        if name in ("color", "background", "background-color", "border-color",
                    "fill", "stroke", "outline-color") or name.startswith("--"):
            for raw_color in COLOR_PATTERN.findall(value):
                normalized = _hex(raw_color)
                if not normalized:
                    continue
                score = 1
                evidence = name + " @ " + selector[:110]
                if any(token in name for token in BRAND_WORDS):
                    score += 14
                if any(token in selector for token in (":root", "html", "body")):
                    score += 3
                if name in ("background-color", "color"):
                    score += 2
                if any(token in name for token in ("background", "text", "neutral", "border")):
                    score += 1
                if normalized in ("#FFFFFF", "#000000"):
                    score -= 2
                item = colors.setdefault(normalized, {"hex": normalized, "score": 0, "evidence": []})
                item["score"] += max(1, score)
                if len(item["evidence"]) < 6 and evidence not in item["evidence"]:
                    item["evidence"].append(evidence)
    ordered = sorted(colors.values(), key=lambda x: (-x["score"], x["hex"]))
    return ordered, dict(font_scores), sorted(font_faces)


def _palette(colors: list[dict], meta_colors: list[tuple[str, str]]) -> dict[str, str]:
    by_hex = {c["hex"]: dict(c) for c in colors}
    for raw, evidence in meta_colors:
        color = _hex(raw)
        if color:
            item = by_hex.setdefault(color, {"hex": color, "score": 0, "evidence": []})
            item["score"] += 20
            item["evidence"].append(evidence)
    ordered = sorted(by_hex.values(), key=lambda x: -x["score"])
    saturated = [c for c in ordered if _saturation(c["hex"]) > 0.20]
    primary = (saturated or ordered or [{"hex": "#444444"}])[0]["hex"]
    common_light = [c for c in ordered if _luminance(c["hex"]) > .86]
    common_dark = [c for c in ordered if _luminance(c["hex"]) < .15]
    return {
        "primary": primary,
        "background": common_light[0]["hex"] if common_light else "#FFFFFF",
        "text": common_dark[0]["hex"] if common_dark else "#161616",
        "neutral": common_dark[0]["hex"] if common_dark else "#242424",
    }


def analyze_site(url: str, *, fetch=None) -> dict:
    """Analyze a page and at most six same-host stylesheets (no JavaScript)."""
    fetch = fetch or _fetch
    page_url, body, content_type = fetch(url, limit=MAX_HTML)
    if "text/html" not in content_type.lower() and b"<html" not in body[:500].lower():
        raise WebsiteScanError("The supplied URL does not return an HTML page")
    parser = _HTMLSignals(page_url)
    parser.feed(_text(body, content_type))
    styles = list(parser.inline_styles)
    failures = []
    stylesheets = []
    host = urlsplit(page_url).hostname
    for stylesheet in list(dict.fromkeys(parser.stylesheets))[:6]:
        if urlsplit(stylesheet).hostname != host:
            failures.append(f"Skipped external CSS: {stylesheet[:140]}")
            continue
        try:
            final, css_body, css_type = fetch(stylesheet, limit=MAX_CSS)
            if urlsplit(final).hostname != host:
                failures.append(f"Skipped redirected external CSS: {stylesheet[:140]}")
                continue
            styles.append(_text(css_body, css_type))
            stylesheets.append(final)
        except WebsiteScanError as exc:
            failures.append(str(exc))
    colors, fonts, font_faces = _css_signals(styles)
    palette = _palette(colors, parser.colors)
    primary_font = max(fonts, key=fonts.get) if fonts else (
        parser.font_hints[0] if parser.font_hints else "Unverified")
    ranked_logos = sorted(parser.logos.values(), key=lambda item: -item["score"])
    for item in ranked_logos:
        item["format"] = Path(urlsplit(item["url"]).path).suffix.lower().lstrip(".") or "unknown"
        item["confidence"] = ("high" if item["score"] >= 60 else
                              "medium" if item["score"] >= 30 else "low")
    site_name = (parser.site_name or parser.title or host or "Unknown").strip()[:120]
    name = re.split(r"\s+[|\-–]\s+", site_name, maxsplit=1)[0].strip() or site_name
    warnings = [
        "Static HTML/CSS inspection only; JavaScript-rendered and computed styles are not evaluated.",
        "Detected colors and logos are candidates, not verified brand guidelines.",
        "Check permissions and font licences before importing assets into production.",
    ] + failures
    if not ranked_logos:
        warnings.append("No explicit logo found. Supply a logo manually.")
    if not colors and not parser.colors:
        warnings.append("No machine-readable colors found; fallback palette needs review.")
    if primary_font == "Unverified":
        warnings.append("No reliable font family found; choose a licensed font manually.")
    output = {
        "schema_version": 1,
        "source_url": page_url,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "palette": palette,
        "colors": colors[:15],
        "typography": {
            "primary": primary_font,
            "families": [{"name": n, "score": score} for n, score in
                         sorted(fonts.items(), key=lambda kv: -kv[1])[:8]],
            "font_faces": font_faces[:12],
            "external_font_hints": list(dict.fromkeys(parser.font_hints))[:8],
        },
        "logos": ranked_logos[:12],
        "warnings": warnings,
        "inspection": {"stylesheets": stylesheets, "inline_css_blocks": len(parser.inline_styles)},
    }
    return output


def suggested_brand(scan: dict, slug: str) -> dict:
    """A reviewable configuration proposal; never overwrites brand.json."""
    return {
        "id": slug,
        "name": scan["name"],
        "version": 1,
        "branding": {"accent": scan["palette"]["primary"]},
        "identity": {
            "typography": {
                "primary": scan["typography"]["primary"],
                "fallback": "DejaVu Sans",
                "status": "Website-derived suggestion; confirm local font availability/licence",
            },
            "palette": scan["palette"],
            "logo": {"candidates": [x["url"] for x in scan["logos"][:5]]},
            "format": {"default_width": 1080, "default_height": 1920, "default_fps": 25},
            "safe_areas": {"top_pixels": 190, "bottom_pixels": 290,
                           "horizontal_pixels": 88},
        },
        "source": {"website": scan["source_url"], "scanned_at": scan["scanned_at"],
                   "status": "unreviewed"},
    }


def download_logo_candidates(scan: dict, target: Path, *, fetch=None) -> list[dict]:
    """Download preview assets only, never overwrite accepted brand assets.

    SVG is retained as source text and deliberately not rasterized here.
    """
    fetch = fetch or _fetch
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    downloaded = []
    seen = set()
    for item in scan.get("logos", []):
        ext = item.get("format", "")
        if ext not in ("svg", "png", "webp", "jpg", "jpeg") or ext in seen:
            continue
        # Higher-scored candidates first, one of each format, up to three files.
        if len(downloaded) >= 3:
            break
        try:
            final, body, mime = fetch(item["url"], limit=MAX_LOGO)
            mimetype = mime.split(";")[0].lower().strip()
            valid = (
                (ext == "png" and body.startswith(b"\x89PNG\r\n\x1a\n"))
                or (ext in ("jpg", "jpeg") and body.startswith(b"\xff\xd8\xff"))
                or (ext == "webp" and body.startswith(b"RIFF") and body[8:12] == b"WEBP")
                or (ext == "svg" and b"<svg" in body[:2048].lower()
                    and b"<!doctype" not in body.lower()
                    and b"<!entity" not in body.lower()
                    and b"<script" not in body.lower()
                    and b"foreignobject" not in body.lower())
            )
            if not valid or mimetype.startswith("text/html"):
                raise WebsiteScanError(f"Logo is not a safe {ext.upper()} file")
            name = f"candidate-logo-{len(downloaded) + 1}.{ext}"
            dest = target / name
            dest.write_bytes(body)
            downloaded.append({
                "source_url": final, "path": str(dest), "format": ext,
                "confidence": item.get("confidence", "low"),
            })
            seen.add(ext)
        except (WebsiteScanError, OSError) as exc:
            scan["warnings"].append(f"Logo candidate could not be downloaded: {exc}")
    return downloaded
