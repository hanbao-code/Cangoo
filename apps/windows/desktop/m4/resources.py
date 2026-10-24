"""Fixed resource catalog for the explicit M4 isolated candidate."""

from __future__ import annotations

from types import MappingProxyType

from desktop.host.resources import ResourceCatalog


class M4ResourceCatalog(ResourceCatalog):
    """Serve the M4 shell without changing the frozen M2/M3 resource set."""

    PRODUCT_SHELL_PATH = "m4_product_shell.html"
    PRODUCT_OUTPUT_KEY = "m4_product.html"
    ASSET_SOURCES = MappingProxyType(
        {
            **ResourceCatalog.ASSET_SOURCES,
            "/transfer.html": ("transfer_shell.html", b"text/html; charset=utf-8"),
            "/scripts/direct_transfer.js": ("scripts/direct_transfer.js", b"text/javascript; charset=utf-8"),
            "/styles/direct_transfer.css": ("styles/direct_transfer.css", b"text/css; charset=utf-8"),
            "/vendor/qwebchannel.js": (
                "vendor/qwebchannel.js",
                b"text/javascript; charset=utf-8",
            ),
            "/scripts/m4_runtime.js": (
                "scripts/m4_runtime.js",
                b"text/javascript; charset=utf-8",
            ),
            "/scripts/focus_visibility.js": (
                "scripts/focus_visibility.js",
                b"text/javascript; charset=utf-8",
            ),
            "/editor.html": (
                "editor_shell.html",
                b"text/html; charset=utf-8",
            ),
            "/scripts/editor_appearance.js": (
                "scripts/editor_appearance.js",
                b"text/javascript; charset=utf-8",
            ),
            "/scripts/editor_runtime.js": (
                "scripts/editor_runtime.js",
                b"text/javascript; charset=utf-8",
            ),
            "/styles/editor.css": (
                "styles/editor.css",
                b"text/css; charset=utf-8",
            ),
            "/note-editor.html": (
                "note_editor_shell.html",
                b"text/html; charset=utf-8",
            ),
            "/scripts/note_editor_runtime.js": (
                "scripts/note_editor_runtime.js",
                b"text/javascript; charset=utf-8",
            ),
            "/styles/note_editor.css": (
                "styles/note_editor.css",
                b"text/css; charset=utf-8",
            ),
            "/styles/focus_visibility.css": (
                "styles/focus_visibility.css",
                b"text/css; charset=utf-8",
            ),
        }
    )


__all__ = ["M4ResourceCatalog"]
