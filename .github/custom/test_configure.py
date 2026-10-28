#!/usr/bin/env python3
"""Fast regression tests for the Firefox ESR overlay; no Firefox build needed."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("configure_firefox.py")
SPEC = importlib.util.spec_from_file_location("configure_firefox", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ConfigureFirefoxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        files = {
            "browser/app/profile/firefox.js": "// test prefs\n",
            "browser/components/places/PlacesBrowserStartup.sys.mjs": (
                "let importBookmarks =\n"
                "      !initialMigrationPerformed &&\n"
                "      (dbStatus == lazy.PlacesUtils.history.DATABASE_STATUS_CREATE ||\n"
                "        dbStatus == lazy.PlacesUtils.history.DATABASE_STATUS_CORRUPT);\n"
            ),
            "browser/branding/unofficial/configure.sh": "MOZ_APP_DISPLAYNAME=Nightly\n",
            "browser/branding/unofficial/locales/en-US/brand.ftl": (
                "-brand-shorter-name = Nightly\n-brand-short-name = Nightly\n"
                "-brand-shortcut-name = Nightly\n-brand-full-name = Nightly\n"
                "-brand-product-name = Firefox\n-vendor-short-name = Mozilla\n"
            ),
            "browser/branding/unofficial/locales/en-US/brand.properties": (
                "brandShorterName=Nightly\nbrandShortName=Nightly\nbrandFullName=Nightly\n"
            ),
            "browser/branding/unofficial/branding.nsi": (
                '!define BrandFullNameInternal "Mozilla Developer Preview"\n'
                '!define BrandFullName "Mozilla Developer Preview"\n'
                '!define CompanyName "mozilla.org"\n'
            ),
        }
        for relative, content in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        asset = self.root / "browser/branding/unofficial/default16.png"
        asset.write_bytes(MODULE.transparent_png(16, 16))
        (asset.parent / "firefox.ico").write_bytes(MODULE.transparent_ico())
        (asset.parent / "content").mkdir()
        (asset.parent / "content/about-logo.svg").write_text("<svg/>", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_overlay_is_applied_and_idempotent(self) -> None:
        MODULE.configure_firefox(self.root)
        MODULE.configure_firefox(self.root)

        prefs = (self.root / "browser/app/profile/firefox.js").read_text(encoding="utf-8")
        self.assertIn('pref("browser.startup.homepage", "about:blank");', prefs)
        self.assertIn('pref("browser.ml.enable", false);', prefs)
        self.assertEqual(prefs.count(MODULE.PREFS_MARKER), 1)

        places = (self.root / "browser/components/places/PlacesBrowserStartup.sys.mjs").read_text()
        self.assertIn("let importBookmarks = false;", places)
        self.assertIn(MODULE.NO_BOOKMARKS_MARKER, places)

        ftl = (self.root / "browser/branding/unofficial/locales/en-US/brand.ftl").read_text()
        self.assertIn("-brand-short-name = Browser", ftl)
        self.assertIn("-brand-product-name = Browser", ftl)
        self.assertNotIn("-brand-product-name = Firefox", ftl)

        self.assertTrue((self.root / "browser/branding/unofficial/default16.png").read_bytes().startswith(b"\x89PNG"))
        self.assertTrue((self.root / "browser/branding/unofficial/firefox.ico").read_bytes().startswith(b"\x00\x00\x01\x00"))

    def test_fails_closed_if_bookmark_initializer_changed(self) -> None:
        startup = self.root / "browser/components/places/PlacesBrowserStartup.sys.mjs"
        startup.write_text("let importBookmarks = true;\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            MODULE.configure_firefox(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
