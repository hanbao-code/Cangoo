"""Build and verify the shared WebEngine frontend canvas.

The committed design host and the generated product shell are deterministic
compositions of ``desktop/frontend``.  This command performs no network access
and never parses the old monolithic prototype.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "desktop" / "frontend"
PROTOTYPE = ROOT / "../../docs/platforms/windows/prototype.html"
MANIFEST = FRONTEND / "source_manifest.json"
DEFAULT_OUTPUT = ROOT / "build" / "web_frontend"

SOURCE_DIRS = ("assets", "design", "scripts", "styles", "vendor")
SOURCE_FILES = (
    "canvas.html",
    "editor_shell.html",
    "note_editor_shell.html",
    "transfer_shell.html",
    "product_shell.html",
    "preview_shell.html",
)
EVENT_ATTRIBUTE_RE = re.compile(r"(?<![\w.-])\b(on[a-z]+)\s*=", re.IGNORECASE)
STYLE_ATTRIBUTE_RE = re.compile(r"(?<![\w.-])\bstyle\s*=", re.IGNORECASE)
REMOTE_REF_RE = re.compile(r"""(?:src|href)\s*=\s*["'](?:https?:)?//""", re.IGNORECASE)
INERT_HANDLER_RE = re.compile(r'\sdata-pdm-on[a-z]+="([^"]*)"', re.IGNORECASE)
CALLED_FUNCTION_RE = re.compile(
    r"(?<![\w$])([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\("
)

PROTOTYPE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'">
<title>小仓 / Cangoo · 原型</title>
<link rel="stylesheet" href="../../../apps/windows/desktop/frontend/styles/tokens.css">
<link rel="stylesheet" href="../../../apps/windows/desktop/frontend/styles/canvas.css">
<link rel="stylesheet" href="../../../apps/windows/desktop/frontend/styles/help.css">
<link rel="stylesheet" href="../../../apps/windows/desktop/frontend/styles/direct_transfer.css">
<link rel="stylesheet" href="../../../apps/windows/desktop/frontend/styles/platform_colors.css">
<link rel="stylesheet" href="../../../apps/windows/desktop/frontend/styles/design_host.css">
<script defer src="../../../apps/windows/desktop/frontend/vendor/zxcvbn.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/vendor/pinyin-pro.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/vendor/dictionaries.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/scripts/help_content.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/scripts/export_selection.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/scripts/canvas_runtime.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/scripts/direct_transfer.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/design/direct_transfer_fixture.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/scripts/help.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/design/inspection_spec.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/scripts/event_dispatcher.js"></script>
<script defer src="../../../apps/windows/desktop/frontend/design/inspector_runtime.js"></script>
</head>
<body class="design-host">
<div id="canvas-stage">
  <div id="ruler-corner"></div>
  <div id="ruler-top"></div>
  <div id="ruler-left"></div>
  <div id="canvas-frame">
    <div id="canvas-badge">1200 × 800 px</div>
{{CANVAS_HTML}}
  </div>
</div>
{{INSPECTOR_HTML}}
</body>
</html>
"""

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").rstrip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.rstrip() + "\n")


def _compose(template: str) -> str:
    return (
        template.replace("{{CANVAS_HTML}}", _read(FRONTEND / "canvas.html"))
        .replace("{{INSPECTOR_HTML}}", _read(FRONTEND / "design" / "inspector.html"))
        .rstrip()
        + "\n"
    )


def _source_paths() -> list[Path]:
    paths = [FRONTEND / name for name in SOURCE_FILES]
    for dirname in SOURCE_DIRS:
        paths.extend(
            path
            for path in (FRONTEND / dirname).rglob("*")
            if path.is_file()
        )
    return sorted(
        (path for path in paths if path != MANIFEST),
        key=lambda path: path.relative_to(FRONTEND).as_posix(),
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest(
    prototype: str,
    preview: str,
    product: str,
) -> dict[str, object]:
    sources = {
        path.relative_to(FRONTEND).as_posix(): {
            "sha256": _sha256_bytes(path.read_bytes()),
            "bytes": path.stat().st_size,
        }
        for path in _source_paths()
    }
    return {
        "schema_version": 1,
        "generator": "tools/build_web_frontend.py",
        "offline_build": True,
        "canonical_canvas": {
            "path": "canvas.html",
            "sha256": sources["canvas.html"]["sha256"],
        },
        "sources": sources,
        "outputs": {
            "../../docs/platforms/windows/prototype.html": {
                "sha256": _sha256_bytes(prototype.encode("utf-8")),
                "role": "visible design truth and inspection host",
            },
            "preview.html": {
                "sha256": _sha256_bytes(preview.encode("utf-8")),
                "role": "public canvas preview",
            },
            "product.html": {
                "sha256": _sha256_bytes(product.encode("utf-8")),
                "role": "product canvas shell",
            },
        },
    }


def _assert_external_only(html: str, label: str) -> None:
    if re.search(r"<style(?:\s|>)", html, re.IGNORECASE):
        raise ValueError(f"{label}: inline style block found")
    for match in re.finditer(r"<script\b([^>]*)>", html, re.IGNORECASE):
        if not re.search(r"\bsrc\s*=", match.group(1), re.IGNORECASE):
            raise ValueError(f"{label}: inline script block found")
    if EVENT_ATTRIBUTE_RE.search(html):
        raise ValueError(f"{label}: executable inline event handler found")
    if STYLE_ATTRIBUTE_RE.search(html):
        raise ValueError(f"{label}: inline style attribute found")
    if REMOTE_REF_RE.search(html):
        raise ValueError(f"{label}: remote resource reference found")


def _assert_sources() -> None:
    owned_paths = [
        FRONTEND / "canvas.html",
        *(FRONTEND / "scripts").glob("*.js"),
        *(FRONTEND / "design").glob("*.js"),
    ]
    combined = "\n".join(_read(path) for path in owned_paths)
    if EVENT_ATTRIBUTE_RE.search(combined):
        raise ValueError("shared source: executable inline event handler found")
    if STYLE_ATTRIBUTE_RE.search(combined):
        raise ValueError("shared source: inline style attribute found")
    _assert_external_only(
        _read(FRONTEND / "editor_shell.html"),
        "editor shell",
    )
    _assert_external_only(
        _read(FRONTEND / "note_editor_shell.html"),
        "note editor shell",
    )
    _assert_external_only(_read(FRONTEND / "transfer_shell.html"), "transfer shell")


def _assert_dispatcher_coverage() -> None:
    product_source = "\n".join(
        [
            _read(FRONTEND / "canvas.html"),
            _read(FRONTEND / "scripts" / "canvas_runtime.js"),
        ]
    )
    dispatcher = _read(FRONTEND / "scripts" / "event_dispatcher.js")
    block = re.search(
        r"const ALLOWED_ACTIONS = new Set\(\[(.*?)\]\);",
        dispatcher,
        re.DOTALL,
    )
    if not block:
        raise ValueError("event dispatcher allowlist was not found")
    allowed = set(re.findall(r"'([A-Za-z_$][\w$]*)'", block.group(1)))
    ignored = {"event", "escapeHtml", "if", "t", "this"}
    required = {
        call.split(".", 1)[0]
        for handler in INERT_HANDLER_RE.findall(product_source)
        for call in CALLED_FUNCTION_RE.findall(handler)
        if call.split(".", 1)[0] not in ignored
    }
    missing = sorted(required - allowed)
    if missing:
        raise ValueError(f"event dispatcher is missing product actions: {missing}")


def _copy_product_assets(output: Path) -> None:
    for dirname in ("assets", "scripts", "styles", "vendor"):
        source = FRONTEND / dirname
        target = output / dirname
        shutil.copytree(source, target, dirs_exist_ok=True)
    design_css = output / "styles" / "design_host.css"
    if design_css.exists():
        design_css.unlink()


def _prepare_help_script(write_committed: bool) -> None:
    help_content = json.loads(_read(FRONTEND / "assets/help/content.json"))
    help_script = "/* 由 build_web_frontend.py 从帮助内容生成，请修改 JSON 来源。 */\nwindow.PDM_HELP_CONTENT = " + json.dumps(help_content, ensure_ascii=False, indent=2) + ";\n"
    help_path = FRONTEND / "scripts/help_content.js"
    if write_committed:
        _write(help_path, help_script)
    elif not help_path.exists() or help_path.read_text(encoding="utf-8") != help_script:
        raise ValueError("help_content.js is stale; run build_web_frontend.py")


def build_product_only(check_only: bool) -> None:
    """公开源码只构建正式产品，不依赖内部设计画布和验收文档。"""
    import sys
    sys.path.insert(0, str(ROOT))
    from desktop.application.resources import ProductResourceCatalog
    from desktop.host.resources import _compose_product

    _prepare_help_script(not check_only)
    product = _compose_product(FRONTEND, ProductResourceCatalog.PRODUCT_SHELL_PATH).decode("utf-8")
    _assert_external_only(product, "product")
    _assert_sources()
    _assert_dispatcher_coverage()
    if not check_only:
        names = {"canvas.html", ProductResourceCatalog.PRODUCT_SHELL_PATH,
                 *(name for name, _mime in ProductResourceCatalog.ASSET_SOURCES.values())}
        manifest = {
            "schema_version": 1,
            "generator": "tools/build_web_frontend.py --product-only",
            "offline_build": True,
            "sources": {name: {"sha256": _sha256_bytes((FRONTEND / name).read_bytes()),
                               "bytes": (FRONTEND / name).stat().st_size}
                        for name in sorted(names)},
            "outputs": {ProductResourceCatalog.PRODUCT_OUTPUT_KEY: {
                "sha256": _sha256_bytes(product.encode("utf-8")),
                "role": "product canvas shell"}},
        }
        _write(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
    ProductResourceCatalog(root=FRONTEND)
    print("Product frontend resources are current.")


def build(
    output: Path,
    write_committed: bool,
) -> tuple[str, str, str, dict[str, object]]:
    _prepare_help_script(write_committed)
    prototype = _compose(PROTOTYPE_TEMPLATE)
    preview = _compose(_read(FRONTEND / "preview_shell.html"))
    product = _compose(
        _read(FRONTEND / "product_shell.html")
    )
    _assert_external_only(prototype, "prototype")
    _assert_external_only(preview, "preview")
    _assert_external_only(product, "product")
    _assert_sources()
    _assert_dispatcher_coverage()

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    _copy_product_assets(output)
    _write(output / "preview.html", preview)
    _write(output / "product.html", product)
    _write(output / "transfer.html", _read(FRONTEND / "transfer_shell.html"))

    manifest = _manifest(prototype, preview, product)
    _write(output / "source_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    if write_committed:
        _write(PROTOTYPE, prototype)
        _write(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
    return prototype, preview, product, manifest


def check() -> None:
    with tempfile.TemporaryDirectory(prefix="pdm-web-frontend-") as temp:
        prototype, _, _, manifest = build(
            Path(temp),
            write_committed=False,
        )
    expected_prototype = PROTOTYPE.read_text(encoding="utf-8")
    if prototype != expected_prototype:
        raise SystemExit("../../docs/platforms/windows/prototype.html is stale; run build_web_frontend.py")
    expected_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest != expected_manifest:
        raise SystemExit("desktop/frontend/source_manifest.json is stale; run build_web_frontend.py")
    print("Shared WebEngine frontend sources and generated design host are current.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--product-only", action="store_true", help="仅处理公开发行的正式产品资源")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.product_only:
        build_product_only(args.check)
    elif args.check:
        check()
    else:
        build(args.output.resolve(), write_committed=True)
        print(f"Built product canvas at {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
