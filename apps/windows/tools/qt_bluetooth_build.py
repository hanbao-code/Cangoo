"""为冻结构建装入已验收的 QtBluetooth 和对应源码材料。"""

import json
from pathlib import Path

from tools.build_windows_installer import sha256


ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / "packaging/windows"
SOURCE_FILES = (
    "tools/qt_bluetooth_build.py",
    "packaging/windows/qt_bluetooth_lock.json",
    "packaging/windows/qt_bluetooth_6_9_3.patch",
    "packaging/windows/qt_bluetooth_build.md",
)


def prepare_inputs(root: Path = ROOT) -> tuple[Path, list[tuple[str, str]]]:
    packaging = root / "packaging/windows"
    lock = json.loads((packaging / "qt_bluetooth_lock.json").read_text(encoding="utf-8"))
    workspace = root.parents[1] if root.name == "windows" and root.parent.name == "apps" else root
    support = workspace / "build_support/qt_bluetooth/6_9_3"
    dll = support / "Qt6Bluetooth.dll"
    archive = support / "qtconnectivity-everywhere-src-6.9.3.tar.xz"
    patch = packaging / "qt_bluetooth_6_9_3.patch"
    for path, expected in ((dll, lock["dll_sha256"]), (archive, lock["source"]["sha256"]),
                           (patch, lock["patch_sha256"])):
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"QtBluetooth 构建材料缺失或摘要不符：{path}；请按 qt_bluetooth_build.md 准备")
    destination = "third_party/qt_bluetooth"
    return dll, [(str(path), destination) for path in (
        archive, patch, packaging / "qt_bluetooth_lock.json", packaging / "qt_bluetooth_build.md",
    )]


def replace_binary(binaries: list, dll: Path) -> int:
    """只允许替换对应 PySide 运行库；开发环境中的原文件不改。"""
    lock = json.loads((PACKAGING / "qt_bluetooth_lock.json").read_text(encoding="utf-8"))
    count = 0
    for index, (destination, source, kind) in enumerate(binaries):
        if Path(destination).name.lower() != "qt6bluetooth.dll":
            continue
        if destination.replace("\\", "/") != "PySide6/Qt6Bluetooth.dll" or kind != "BINARY":
            raise ValueError("QtBluetooth 收集位置或类型异常")
        if sha256(Path(source)) != lock["original_dll_sha256"] or sha256(dll) != lock["dll_sha256"]:
            raise ValueError("QtBluetooth 原运行库或补丁 DLL 摘要不符")
        binaries[index] = (destination, str(dll), kind)
        count += 1
    return count
