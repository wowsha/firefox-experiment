#!/usr/bin/env python3
"""Apply the Browser product overlay to a clean Firefox ESR source snapshot."""

from __future__ import annotations

import re
import struct
import sys
import zlib
from pathlib import Path

PREFS_MARKER = "// Browser project defaults (managed by .github/custom/configure_firefox.py)"
NO_BOOKMARKS_MARKER = "MINIMAL_BROWSER_NO_DEFAULT_BOOKMARKS"

PREFS = [
    'pref("browser.startup.homepage", "about:blank");',
    'pref("browser.startup.page", 0);',
    'pref("browser.newtabpage.enabled", false);',
    'pref("browser.newtabpage.activity-stream.showSponsored", false);',
    'pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);',
    'pref("browser.newtabpage.activity-stream.feeds.topsites", false);',
    'pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);',
    'pref("browser.newtabpage.activity-stream.feeds.section.highlights", false);',
    'pref("browser.newtabpage.activity-stream.showSearch", false);',
    'pref("browser.newtabpage.activity-stream.showWeather", false);',
    'pref("browser.urlbar.suggest.quicksuggest.sponsored", false);',
    'pref("browser.urlbar.suggest.quicksuggest.nonsponsored", false);',
    'pref("browser.urlbar.suggest.searches", false);',
    'pref("browser.search.suggest.enabled", false);',
    'pref("browser.discovery.enabled", false);',
    'pref("browser.promo.focus.enabled", false);',
    'pref("browser.shopping.experience2023.enabled", false);',
    'pref("extensions.htmlaboutaddons.recommendations.enabled", false);',
    'pref("extensions.pocket.enabled", false);',
    'pref("browser.ml.enable", false);',
    'pref("browser.ml.chat.enabled", false);',
    'pref("browser.ml.chat.shortcuts", false);',
    'pref("browser.ml.linkPreview.enabled", false);',
    'pref("browser.bookmarks.restore_default_bookmarks", false);',
    'pref("browser.places.importBookmarksHTML", false);',
    'pref("browser.bookmarks.showMobileBookmarks", false);',
    'pref("browser.toolbars.bookmarks.visibility", "never");',
    'pref("app.shield.optoutstudies.enabled", false);',
    'pref("datareporting.healthreport.uploadEnabled", false);',
    'pref("toolkit.telemetry.enabled", false);',
    'pref("toolkit.telemetry.unified", false);',
    'pref("browser.ping-centre.telemetry", false);',
    'pref("app.update.enabled", false);',
    'pref("browser.contentblocking.category", "strict");',
    'pref("privacy.trackingprotection.enabled", true);',
    'pref("privacy.trackingprotection.pbmode.enabled", true);',
]


def png_chunk(kind: bytes, data: bytes) -> bytes:
    payload = kind + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)


def transparent_png(width: int, height: int) -> bytes:
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        width, height = 1, 1
    rows = b"".join(b"\x00" + (b"\x00" * (width * 4)) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(rows, 9))
        + png_chunk(b"IEND", b"")
    )


def transparent_ico() -> bytes:
    png = transparent_png(64, 64)
    return struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22) + png


def white_bmp(width: int, height: int) -> bytes:
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        width, height = 1, 1
    row_size = (width * 3 + 3) & ~3
    pixels = (b"\xff\xff\xff" * width + b"\x00" * (row_size - width * 3)) * height
    image_size = len(pixels)
    file_header = struct.pack("<2sIHHI", b"BM", 54 + image_size, 0, 0, 54)
    dib_header = struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, image_size, 2835, 2835, 0, 0)
    return file_header + dib_header + pixels


def set_line_values(text: str, patterns: list[tuple[str, str]], path: Path) -> str:
    for pattern, replacement in patterns:
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
        if count != 1:
            raise RuntimeError(f"Expected one branding setting matching {pattern!r} in {path}")
    return text


def patch_branding(root: Path) -> None:
    branding = root / "browser/branding/unofficial"

    configure = branding / "configure.sh"
    text = configure.read_text(encoding="utf-8")
    text = set_line_values(text, [(r"^MOZ_APP_DISPLAYNAME=.*$", "MOZ_APP_DISPLAYNAME=Browser")], configure)
    configure.write_text(text, encoding="utf-8")

    ftl = branding / "locales/en-US/brand.ftl"
    text = ftl.read_text(encoding="utf-8")
    text = set_line_values(
        text,
        [
            (r"^-brand-shorter-name\s*=.*$", "-brand-shorter-name = Browser"),
            (r"^-brand-short-name\s*=.*$", "-brand-short-name = Browser"),
            (r"^-brand-shortcut-name\s*=.*$", "-brand-shortcut-name = Browser"),
            (r"^-brand-full-name\s*=.*$", "-brand-full-name = Browser"),
            (r"^-brand-product-name\s*=.*$", "-brand-product-name = Browser"),
            (r"^-vendor-short-name\s*=.*$", "-vendor-short-name = Browser"),
        ],
        ftl,
    )
    ftl.write_text(text, encoding="utf-8")

    properties = branding / "locales/en-US/brand.properties"
    text = properties.read_text(encoding="utf-8")
    text = set_line_values(
        text,
        [
            (r"^brandShorterName=.*$", "brandShorterName=Browser"),
            (r"^brandShortName=.*$", "brandShortName=Browser"),
            (r"^brandFullName=.*$", "brandFullName=Browser"),
        ],
        properties,
    )
    properties.write_text(text, encoding="utf-8")

    nsi = branding / "branding.nsi"
    text = nsi.read_text(encoding="utf-8")
    text = set_line_values(
        text,
        [
            (r'^!define BrandFullNameInternal\s+.*$', '!define BrandFullNameInternal "Browser"'),
            (r'^!define BrandFullName\s+.*$', '!define BrandFullName "Browser"'),
            (r'^!define CompanyName\s+.*$', '!define CompanyName "Browser Project"'),
        ],
        nsi,
    )
    nsi.write_text(text, encoding="utf-8")


def patch_default_prefs(root: Path) -> None:
    prefs_file = root / "browser/app/profile/firefox.js"
    text = prefs_file.read_text(encoding="utf-8")
    if PREFS_MARKER not in text:
        text = text.rstrip() + "\n\n" + PREFS_MARKER + "\n" + "\n".join(PREFS) + "\n"
        prefs_file.write_text(text, encoding="utf-8")

    startup = root / "browser/components/places/PlacesBrowserStartup.sys.mjs"
    text = startup.read_text(encoding="utf-8")
    if NO_BOOKMARKS_MARKER not in text:
        pattern = re.compile(
            r"let importBookmarks =\s*!initialMigrationPerformed &&\s*"
            r"\(\s*dbStatus == lazy\.PlacesUtils\.history\.DATABASE_STATUS_CREATE\s*\|\|\s*"
            r"dbStatus == lazy\.PlacesUtils\.history\.DATABASE_STATUS_CORRUPT\s*\);",
            re.MULTILINE,
        )
        replacement = f"let importBookmarks = false; // {NO_BOOKMARKS_MARKER}"
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise RuntimeError(
                "Could not disable the upstream default-bookmark import in "
                f"{startup}; review the ESR source change before building."
            )
        startup.write_text(text, encoding="utf-8")


def neutralize_brand_assets(root: Path) -> None:
    branding = root / "browser/branding/unofficial"
    for path in branding.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        is_png_logo = (
            (name.startswith("default") and name.endswith(".png"))
            or (name.startswith("PrivateBrowsing") and name.endswith(".png"))
            or (name.startswith("VisualElements") and name.endswith(".png"))
            or (name.startswith("about-logo") and name.endswith(".png"))
            or name in {"about.png", "background.png"}
        )
        if is_png_logo:
            raw = path.read_bytes()
            if raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) >= 24:
                width, height = struct.unpack(">II", raw[16:24])
                path.write_bytes(transparent_png(width, height))
        elif path.suffix.lower() == ".ico" and name in {
            "firefox.ico", "firefox64.ico", "newtab.ico", "newwindow.ico", "pbmode.ico"
        }:
            path.write_bytes(transparent_ico())
        elif path.suffix.lower() == ".bmp" and name in {"wizHeader.bmp", "wizHeaderRTL.bmp", "wizWatermark.bmp"}:
            raw = path.read_bytes()
            if raw[:2] == b"BM" and len(raw) >= 26:
                width, height = struct.unpack("<ii", raw[18:26])
                path.write_bytes(white_bmp(abs(width), abs(height)))
        elif name in {"about-logo.svg", "about-logo@2x.svg", "about-wordmark.svg", "firefox-wordmark.svg"}:
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>\n', encoding="utf-8")


def configure_firefox(source: Path) -> None:
    source = source.resolve()
    required = [
        source / "browser/app/profile/firefox.js",
        source / "browser/components/places/PlacesBrowserStartup.sys.mjs",
        source / "browser/branding/unofficial/configure.sh",
        source / "browser/branding/unofficial/locales/en-US/brand.ftl",
        source / "browser/branding/unofficial/locales/en-US/brand.properties",
        source / "browser/branding/unofficial/branding.nsi",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required Firefox ESR source files are missing:\n" + "\n".join(missing))
    patch_default_prefs(source)
    patch_branding(source)
    neutralize_brand_assets(source)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} PATH_TO_FIREFOX_SOURCE", file=sys.stderr)
        raise SystemExit(2)
    configure_firefox(Path(sys.argv[1]))
    print("Applied minimal Browser defaults, blank branding assets, and no-bookmark initialization.")
