"""正式产品页面及独立编辑、备份、传输窗口的固定资源目录。"""

from __future__ import annotations

from types import MappingProxyType

from desktop.host.resources import ResourceCatalog


class ProductResourceCatalog(ResourceCatalog):
    """在基础资源白名单上提供正式主页面与受限独立窗口。"""

    PRODUCT_SHELL_PATH = "product_shell.html"
    PRODUCT_OUTPUT_KEY = "product.html"
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
            "/scripts/product_runtime.js": (
                "scripts/product_runtime.js",
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


__all__ = ["ProductResourceCatalog"]
