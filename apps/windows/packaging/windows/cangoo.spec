# Windows 目录式候选：主程序无控制台，评分程序保留匿名管道。
from pathlib import Path
import os
import sys

root = Path(SPECPATH).resolve().parents[1]
sys.path.insert(0, str(root))

# 在任何Qt导入前收敛DLL搜索路径，避免借用运行构建工具的外部环境。
windows = Path(os.environ["SystemRoot"]).resolve()
base_python = Path(sys.base_prefix).resolve()
venv = Path(sys.prefix).resolve()
os.environ["PATH"] = os.pathsep.join(str(path) for path in (
    venv / "Scripts", base_python, base_python / "DLLs", windows / "System32", windows,
))

from desktop.m4.contract import load_m4_contract
from desktop.m4.resources import M4ResourceCatalog
from tools.build_windows_installer import read_product_version
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct,
)

product_version, file_version = read_product_version()
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=file_version, prodvers=file_version, fileType=1),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'hanbao-code'),
        StringStruct('FileDescription', 'Cangoo'),
        StringStruct('FileVersion', '.'.join(str(part) for part in file_version)),
        StringStruct('ProductName', 'Cangoo'),
        StringStruct('ProductVersion', product_version),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
)

# 构建前使用正式加载器检查固定资源，不复制整棵开发文档或测试目录。
load_m4_contract()
M4ResourceCatalog()
frontend_sources = {
    "canvas.html",
    "m4_product_shell.html",
    "source_manifest.json",
    *(source for source, _mime in M4ResourceCatalog.ASSET_SOURCES.values()),
}
datas = [
    (str(root / "desktop/frontend" / name), str(Path("desktop/frontend") / Path(name).parent))
    for name in sorted(frontend_sources)
]
for directory, pattern in (
    ("core/dictionaries", "*.txt"),
    ("core/i18n", "*.json"),
    ("resources/icons/cangoo", "*.ico"),
):
    datas.extend((str(path), directory) for path in sorted((root / directory).glob(pattern)))
datas.append((str(root / "contracts/bridge_contract_v1.json"), "contracts"))

main = Analysis([str(root / "desktop/product_app.py")], pathex=[str(root)], datas=datas,
                hiddenimports=["desktop.host.lan_access", "desktop.host.lan_access_native"],
                hookspath=[str(root / "packaging/windows/hooks")],
                excludes=["cffi._shimmed_dist_utils"])
worker = Analysis([str(root / "desktop/m4/strength_worker.py")], pathex=[str(root)])

for analysis in (main, worker):
    for destination, source, kind in analysis.binaries:
        actual = Path(source).resolve(strict=True)
        if not any(actual.is_relative_to(allowed) for allowed in (venv, base_python, windows)):
            raise ValueError(f"未批准的二进制来源：{destination}: {actual}")
        # 防止曾经误收集的非产品Qt扩展重新进入发行包。
        if Path(destination).name in {
            "Qt6Charts.dll", "Qt6DataVisualization.dll", "Qt6Graphs.dll",
            "Qt6Quick3D.dll", "Qt6Quick3DUtils.dll", "Qt6QuickTimeline.dll",
            "Qt6VirtualKeyboard.dll",
        }:
            raise ValueError(f"非产品Qt扩展被收集：{destination}")
app = EXE(
    PYZ(main.pure), main.scripts, [],
    exclude_binaries=True, name="Cangoo", console=False, upx=False,
    icon=str(root / "resources/icons/cangoo/app.ico"),
    version=version_info,
)
helper = EXE(
    PYZ(worker.pure), worker.scripts, [],
    exclude_binaries=True, name="cangoo_strength_worker", console=True, upx=False,
    icon=str(root / "resources/icons/cangoo/app.ico"),
    version=version_info,
)
COLLECT(
    app, helper, main.binaries, worker.binaries, main.datas, worker.datas,
    name="Cangoo", upx=False,
)
