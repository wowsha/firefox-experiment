# Browser build overlay

This directory contains the product overlay applied to the Firefox ESR source snapshot in the **esr** branch. The upstream snapshot itself remains free of product-specific patches, making manual ESR updates simpler.

## What the build changes

- Sets the product display name to **Browser** and replaces unofficial-brand icon/wordmark assets with transparent assets.
- Starts with about:blank, hides the bookmarks toolbar, and patches first-run Places initialization so new profiles do not get Firefox's built-in bookmarks.
- Disables sponsored new-tab content, browser promotions, telemetry uploads, studies, search suggestions, built-in browser ML/AI entry points, and the built-in software-update prompt.
- Uses Firefox's **Strict** Enhanced Tracking Protection and installs the signed **uBlock Origin** extension from Mozilla Add-ons into the distribution directory.
- Keeps ordinary browser features such as tabs, navigation, downloads, password manager, developer tools, and user-created bookmarks.

The extension is fetched from Mozilla Add-ons at build time, so builds are not fully offline/reproducible. The build deliberately fails if the upstream Places initialization code changes in a way that prevents the no-default-bookmarks patch.

## GitHub Actions

Open **Actions → Build and test Browser → Run workflow** to build the current ESR snapshot. The run uploads separate Linux and Windows artifacts; each includes a screenshot. The Linux artifact contains a .deb package. The Windows artifact contains a full installer built by Firefox's own mach package command.

Open **Actions → Update Firefox ESR → Run workflow** to import the newest tagged Firefox ESR source snapshot (or enter a specific ESR release tag). The **esr** branch is intentionally replaced with a clean upstream snapshot; customization lives here on **main** and is applied at build time. A successful update automatically starts the build workflow.

## Tests and resource notes

CI runs overlay regression tests, Firefox's existing New Tab and Places test suites, and a browser startup/screenshot test. Passing these tests is useful evidence, but it cannot prove that the browser is bug-free.

A full Firefox compile is resource-intensive. Mozilla's build documentation recommends roughly 30 GB free on Linux and 40 GB on Windows. If a standard hosted runner runs out of disk or time, use a larger GitHub-hosted runner or a suitably provisioned self-hosted runner.
