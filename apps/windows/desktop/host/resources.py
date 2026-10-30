"""Fixed, integrity-checked resources for the ``pdm://app`` origin."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Mapping

from PySide6.QtCore import QUrl


APP_SCHEME = b"pdm"
APP_HOST = "app"
APP_ORIGIN = "pdm://app"
ENTRY_PATH = "/index.html"
ENTRY_URL = f"{APP_ORIGIN}{ENTRY_PATH}"


@dataclass(frozen=True)
class ResourcePayload:
    """Immutable bytes and MIME metadata returned by the scheme handler."""

    content: bytes
    mime_type: bytes


class ResourceIntegrityError(RuntimeError):
    """The committed frontend sources no longer match their source manifest."""


_ASSET_SOURCES: Mapping[str, tuple[str, bytes]] = MappingProxyType(
    {
        "/assets/brand/cangoo.png": (
            "assets/brand/cangoo.png",
            b"image/png",
        ),
        "/styles/tokens.css": ("styles/tokens.css", b"text/css; charset=utf-8"),
        "/styles/canvas.css": ("styles/canvas.css", b"text/css; charset=utf-8"),
        "/styles/platform_colors.css": (
            "styles/platform_colors.css",
            b"text/css; charset=utf-8",
        ),
        "/assets/help/connect_zh.png": ("assets/help/connect_zh.png", b"image/png"),
        "/assets/help/connect_en.png": ("assets/help/connect_en.png", b"image/png"),
        "/assets/help/vault_zh.png": ("assets/help/vault_zh.png", b"image/png"),
        "/assets/help/vault_en.png": ("assets/help/vault_en.png", b"image/png"),
        "/assets/help/notes_zh.png": ("assets/help/notes_zh.png", b"image/png"),
        "/assets/help/notes_en.png": ("assets/help/notes_en.png", b"image/png"),
        "/assets/help/health_zh.png": ("assets/help/health_zh.png", b"image/png"),
        "/assets/help/health_en.png": ("assets/help/health_en.png", b"image/png"),
        "/assets/help/tools_zh.png": ("assets/help/tools_zh.png", b"image/png"),
        "/assets/help/tools_en.png": ("assets/help/tools_en.png", b"image/png"),
        "/assets/help/settings_zh.png": ("assets/help/settings_zh.png", b"image/png"),
        "/assets/help/settings_en.png": ("assets/help/settings_en.png", b"image/png"),
        "/assets/help/backup_zh.png": ("assets/help/backup_zh.png", b"image/png"),
        "/assets/help/backup_en.png": ("assets/help/backup_en.png", b"image/png"),
        "/assets/help/content.json": ("assets/help/content.json", b"application/json"),
        "/scripts/help_content.js": ("scripts/help_content.js", b"text/javascript; charset=utf-8"),
        "/scripts/help.js": ("scripts/help.js", b"text/javascript; charset=utf-8"),
        "/scripts/export_selection.js": ("scripts/export_selection.js", b"text/javascript; charset=utf-8"),
        "/styles/help.css": ("styles/help.css", b"text/css; charset=utf-8"),
        "/scripts/canvas_runtime.js": (
            "scripts/canvas_runtime.js",
            b"text/javascript; charset=utf-8",
        ),
        "/scripts/event_dispatcher.js": (
            "scripts/event_dispatcher.js",
            b"text/javascript; charset=utf-8",
        ),
        "/scripts/security_lifecycle.js": (
            "scripts/security_lifecycle.js",
            b"text/javascript; charset=utf-8",
        ),
        "/scripts/preview_entry.js": (
            "scripts/preview_entry.js",
            b"text/javascript; charset=utf-8",
        ),
        "/vendor/zxcvbn.js": (
            "vendor/zxcvbn.js",
            b"text/javascript; charset=utf-8",
        ),
        "/vendor/pinyin-pro.js": (
            "vendor/pinyin-pro.js",
            b"text/javascript; charset=utf-8",
        ),
        "/vendor/dictionaries.js": (
            "vendor/dictionaries.js",
            b"text/javascript; charset=utf-8",
        ),
        "/assets/fonts/Manrope-Variable.ttf": (
            "assets/fonts/Manrope-Variable.ttf",
            b"font/ttf",
        ),
        "/assets/fonts/JetBrainsMono-Regular.ttf": (
            "assets/fonts/JetBrainsMono-Regular.ttf",
            b"font/ttf",
        ),
    }
)


def frontend_root() -> Path:
    """Return the bundled frontend root without consulting user-controlled paths."""

    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / "desktop" / "frontend"
    return Path(__file__).resolve().parents[1] / "frontend"


def application_icon():
    """系统、窗口与托盘共用原色图标，不随连接状态切换。"""
    from PySide6.QtGui import QIcon

    return QIcon(str(frontend_root().parents[1] / "resources/icons/cangoo/app.ico"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_source(root: Path, relative_path: str) -> bytes:
    path = root / Path(relative_path)
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ResourceIntegrityError(
            f"bundled resource is missing or unreadable: {relative_path}"
        ) from exc


def _compose_product(root: Path, shell_path: str) -> bytes:
    shell = _read_source(root, shell_path).decode("utf-8").rstrip()
    canvas = _read_source(root, "canvas.html").decode("utf-8").rstrip()
    if shell.count("{{CANVAS_HTML}}") != 1:
        raise ResourceIntegrityError("product shell must contain one canvas marker")
    return (shell.replace("{{CANVAS_HTML}}", canvas).rstrip() + "\n").encode("utf-8")


class ResourceCatalog:
    """A closed resource map; request paths are never translated to disk paths."""

    PRODUCT_SHELL_PATH = "preview_shell.html"
    PRODUCT_OUTPUT_KEY = "preview.html"
    ASSET_SOURCES = _ASSET_SOURCES

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or frontend_root()).resolve()
        self._resources = self._load_verified_resources()

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(self._resources))

    def payload_for_url(self, url: QUrl) -> ResourcePayload | None:
        """Return a whitelisted payload or ``None`` for every other URL."""

        path = url.path()
        if (
            not url.isValid()
            or url.scheme().lower() != "pdm"
            or url.host().lower() != APP_HOST
            or url.userInfo()
            or url.port(-1) != -1
            or url.hasQuery()
            or url.hasFragment()
            or url.path(QUrl.ComponentFormattingOption.FullyEncoded) != path
        ):
            return None
        return self._resources.get(path)

    def _load_verified_resources(self) -> Mapping[str, ResourcePayload]:
        manifest_bytes = _read_source(self.root, "source_manifest.json")
        try:
            manifest = json.loads(manifest_bytes.decode("utf-8"))
            source_manifest = manifest["sources"]
            expected_product = manifest["outputs"][
                self.PRODUCT_OUTPUT_KEY
            ]["sha256"]
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ResourceIntegrityError("frontend source manifest is invalid") from exc

        required_sources = {
            "canvas.html",
            self.PRODUCT_SHELL_PATH,
            *(
                relative
                for relative, _mime in self.ASSET_SOURCES.values()
            ),
        }
        source_bytes: dict[str, bytes] = {}
        for relative_path in sorted(required_sources):
            data = _read_source(self.root, relative_path)
            entry = source_manifest.get(relative_path)
            if not isinstance(entry, dict) or entry.get("sha256") != _sha256(data):
                raise ResourceIntegrityError(
                    f"frontend source hash mismatch: {relative_path}"
                )
            source_bytes[relative_path] = data

        product = _compose_product(
            self.root,
            self.PRODUCT_SHELL_PATH,
        )
        if _sha256(product) != expected_product:
            raise ResourceIntegrityError("composed product entry hash mismatch")

        resources: dict[str, ResourcePayload] = {
            ENTRY_PATH: ResourcePayload(product, b"text/html; charset=utf-8")
        }
        for url_path, (
            relative_path,
            mime_type,
        ) in self.ASSET_SOURCES.items():
            resources[url_path] = ResourcePayload(
                source_bytes[relative_path],
                mime_type,
            )
        return MappingProxyType(resources)
