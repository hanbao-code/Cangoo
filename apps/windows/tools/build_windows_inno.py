"""从当前源码冻结完整程序并生成本地 Inno 安装候选；不执行安装或启动产品。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import marshal
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import CodeType

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1] if ROOT.name == "windows" and ROOT.parent.name == "apps" else ROOT
sys.path.insert(0, str(ROOT))

from tools.build_windows_installer import read_product_version, sha256, write_manifest
from tools.work_root import ProjectWorkRoot
from tools.qt_bluetooth_build import SOURCE_FILES

HOOK_NAME = "cangoo_acceptance_runtime"
HOOK_ENV = "CANGOO_ACCEPTANCE_RUNTIME_HOOK"
INNO_SOURCE = ROOT / "packaging/windows"
NATIVE_SOURCE = ROOT / "packaging/windows/native"


def verify_inno_toolchain(iscc: Path) -> dict:
    lock = json.loads((ROOT / "packaging/windows/inno_tool_lock.json").read_text(encoding="utf-8"))
    if lock["version"] != "7.1.0" or iscc.name.lower() != "iscc.exe":
        raise ValueError("本构建仅支持固定的 Inno Setup 7.1.0")
    directory = iscc.parent.resolve(strict=True)
    for name, expected in lock["files_sha256"].items():
        path = directory / name
        if not path.resolve(strict=True).is_relative_to(directory) or path.lstat().st_file_attributes & 0x400 or sha256(path) != expected:
            raise ValueError("Inno 7.1.0 工具摘要不符：" + name)
    return lock


def acceptance_configuration(root: Path | None) -> dict:
    if root is None:
        return {"app_id": "hanbao-code.Cangoo", "name": "Cangoo", "machine_leaf": "Cangoo"}
    root = root.absolute()
    work = ProjectWorkRoot.resolve().temporary.resolve(strict=True)
    match = re.fullmatch(r"inno_full_[0-9]{8}_([a-f0-9]{8})", root.name)
    if root.parent.resolve(strict=True) != work or root.resolve(strict=False) != root or not match:
        raise ValueError("验收根必须是工作根临时运行下独立的 inno_full_日期_短ID 目录")
    for directory in (root, *root.parents):
        if directory.exists() and directory.lstat().st_file_attributes & 0x400:
            raise ValueError("验收根不能经过重解析点")
    identifier = match[1]
    return {"app_id": "Cangoo.Inno.Acceptance." + identifier, "name": "小仓·验收-" + identifier,
            "machine_leaf": "CangooInnoAcceptance_" + identifier, "root": str(root),
            "data_root": str(root / "data"), "locations": str(root / "locations"),
            "default_directory": str(root / "locations/Cangoo")}


def write_runtime_hook(root: Path, output: Path) -> Path:
    """路径值编入代码；快捷方式和子进程不依赖启动器提供环境。"""
    output.mkdir(parents=True, exist_ok=True)
    hook = output / (HOOK_NAME + ".py")
    source = '''# 仅用于隔离验收，任一目录被转向时拒绝启动。
import os
from pathlib import Path
import tempfile

_root = Path(ROOT_LITERAL)
_directories = {"APPDATA": _root / "data/roaming", "LOCALAPPDATA": _root / "data/local",
                "USERPROFILE": _root / "data/profile", "HOME": _root / "data/profile",
                "TEMP": _root / "temp", "TMP": _root / "temp", "TMPDIR": _root / "temp"}
def _check_parents(_directory):
    for _parent in (_directory, *_directory.parents):
        if os.path.lexists(_parent) and (_parent.resolve(strict=True) != _parent or _parent.lstat().st_file_attributes & 0x400):
            raise RuntimeError("CANGOO_ACCEPTANCE_DIRECTORY_REDIRECTED")
for _directory in (_root, _root / "data", *_directories.values()):
    _check_parents(_directory)
    _directory.mkdir(parents=True, exist_ok=True)
    _check_parents(_directory)
for _name, _directory in _directories.items():
    os.environ[_name] = str(_directory)
os.environ["HOMEDRIVE"] = _directories["USERPROFILE"].drive
os.environ["HOMEPATH"] = str(_directories["USERPROFILE"])[2:]
tempfile.tempdir = str(_root / "temp")
'''.replace("ROOT_LITERAL", repr(str(root)))
    hook.write_text(source, encoding="utf-8", newline="\n")
    return hook


def frozen_hook_hashes(payload: Path, root: Path | None) -> dict[str, str]:
    """反读两个冻结程序，防止验收仅隔离了构建进程。"""
    from PyInstaller.archive.readers import CArchiveReader

    def constants(code: CodeType):
        for value in code.co_consts:
            if isinstance(value, CodeType):
                yield from constants(value)
            else:
                yield value

    result = {}
    for name in ("Cangoo.exe", "cangoo_strength_worker.exe"):
        archive = CArchiveReader(str(payload / name))
        if root is None:
            if HOOK_NAME in archive.toc:
                raise ValueError("正式程序不能含验收钩子")
            continue
        if HOOK_NAME not in archive.toc:
            raise ValueError("验收程序缺少固定隔离钩子：" + name)
        content = archive.extract(HOOK_NAME)
        if str(root) not in constants(marshal.loads(content)):
            raise ValueError("冻结钩子没有绑定本次验收根：" + name)
        result[name] = hashlib.sha256(content).hexdigest()
    return result


def installer_source_paths() -> tuple[Path, ...]:
    """Inno公开构建所需文件；内部设计与检查不随源码导出。"""
    names = {*SOURCE_FILES, "tools/build_windows_inno.py", "tools/build_windows_packages.py",
             "tools/build_windows_installer.py", "tools/build_web_frontend.py", "tools/work_root.py",
             "packaging/windows/cangoo.spec", "packaging/windows/cangoo.iss",
             "packaging/windows/recovery.iss", "packaging/windows/uninstall_data.iss",
             "packaging/windows/inno_tool_lock.json", "packaging/windows/source_readme.md",
             "packaging/windows/requirements.txt", "packaging/windows/third_party_sources.md"}
    names.update("packaging/windows/native/" + name for name in (
        "inno_support.cpp", "inno_support.h", "install_location.cpp", "install_location.h",
        "user_data_cleanup.cpp", "user_data_cleanup.h", "user_identity.h", "LICENSE"))
    return tuple(sorted(Path(name) for name in names))


def source_hashes() -> dict[str, str]:
    directories = ("core", "desktop", "contracts", "resources",
                   "packaging/windows/native", "packaging/windows/hooks")
    extensions = {".py", ".json", ".txt", ".js", ".css", ".html", ".svg", ".ico", ".png", ".ttf", ".cpp", ".h", ".iss"}
    sources = {path for directory in directories for path in (ROOT / directory).rglob("*")
               if path.is_file() and (path.suffix.lower() in extensions or path.name == "LICENSE")
               and "__pycache__" not in path.parts}
    sources.update(INNO_SOURCE / name for name in ("cangoo.iss", "recovery.iss", "uninstall_data.iss", "inno_tool_lock.json"))
    sources.update(ROOT / name for name in installer_source_paths())
    sources.update(ROOT / name for name in ("packaging/windows/cangoo.spec", "tools/build_windows_inno.py",
                                           "tools/build_windows_installer.py", "tools/build_web_frontend.py", "tools/work_root.py"))
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in sorted(sources)}


def prepare_manifest(payload: Path, output: Path, app_id: str) -> tuple[Path, Path]:
    """根清单登记摘要文件，摘要登记根清单；摘要自身不递归计算。"""
    hashes = payload / "_internal/payload_hashes.txt"
    hashes.write_text("", encoding="utf-8", newline="\n")
    manifest = write_manifest(payload, output, app_id)
    for name in manifest.read_text(encoding="utf-8-sig").splitlines()[1:]:
        if not name or len(name) >= 1024 or any(character in name for character in ":/|") or ".." in name or name.startswith("\\") or name.endswith("\\"):
            raise ValueError("程序清单路径不符合恢复边界")
    values = {path.relative_to(payload).as_posix(): sha256(path) for path in sorted(payload.rglob("*"))
              if path.is_file() and path != hashes}
    values["install_files.txt"] = sha256(manifest)
    lines = [digest + "|" + name.replace("/", "\\") for name, digest in sorted(values.items())]
    hashes.write_text("\n".join(["CANGOO-HASHES-1 " + app_id, *lines]) + "\n",
        encoding="utf-8-sig", newline="\n")
    return manifest, hashes


def payload_hashes(payload: Path) -> dict[str, str]:
    return {path.relative_to(payload).as_posix(): sha256(path)
            for path in sorted(payload.rglob("*")) if path.is_file()}


def acceptance_version_payload(payload: Path, output: Path, version: str) -> Path:
    """每版只增加一个公开标记，供更新和恢复核对不同字节。"""
    target = output / ("payload_" + version.replace(".", "_"))
    shutil.copytree(payload, target)
    (target / "_internal/acceptance_version.txt").write_text(version + "\n", encoding="ascii", newline="\n")
    return target


def build(output: Path, iscc: Path, compiler: Path, *, acceptance_root: Path | None = None,
          test_versions: tuple[str, ...] = ()) -> Path:
    version, _file_version = read_product_version()
    identity = acceptance_configuration(acceptance_root)
    versions = test_versions or (version,)
    if test_versions and acceptance_root is None:
        raise ValueError("测试安装器版本只能用于隔离验收构建")
    if len(set(versions)) != len(versions) or any(not re.fullmatch(r"(?:0|[1-9][0-9]{0,4})(?:\.(?:0|[1-9][0-9]{0,4})){2}", item)
                                                or any(int(part) > 65535 for part in item.split(".")) for item in versions):
        raise ValueError("安装器版本必须是互不重复的三段 Windows 数值版本")
    output = output.absolute()
    if output.exists() or output.resolve(strict=False).is_relative_to(ROOT):
        raise ValueError("构建输出必须是源码目录外的全新目录")
    if acceptance_root is not None and not output.resolve(strict=False).is_relative_to(acceptance_root):
        raise ValueError("验收构建输出必须位于本次验收根")
    iscc, compiler = iscc.resolve(strict=True), compiler.resolve(strict=True)
    if not iscc.is_file() or not compiler.is_file():
        raise ValueError("需要 Inno ISCC.exe 和已配置 x64 INCLUDE/LIB 的 MSVC cl.exe")
    tool_lock = verify_inno_toolchain(iscc)
    before = source_hashes()
    legal = {name: sha256(WORKSPACE / name) for name in ("LICENSE.md", "COPYING", "OPENSSL_EXCEPTION.md")}
    output.mkdir(parents=True)
    for name in ("temp", "cache", "obj"):
        (output / name).mkdir()
    third_party = output / "third_party"
    third_party.mkdir()
    inno_license = third_party / "inno_license.txt"
    shutil.copy2(iscc.parent / tool_lock["license"], inno_license)
    env = {**os.environ, "TEMP": str(output / "temp"), "TMP": str(output / "temp"),
           "PYINSTALLER_CONFIG_DIR": str(output / "cache"), "PYTHONDONTWRITEBYTECODE": "1"}
    for name in ("CL", "_CL_", HOOK_ENV):
        env.pop(name, None)
    hook = write_runtime_hook(acceptance_root, output / "hooks") if acceptance_root else None
    if hook:
        env[HOOK_ENV] = str(hook)
    commands = []
    started = datetime.now(timezone.utc).isoformat()

    def execute(arguments: list[str], name: str) -> None:
        commands.append(arguments)
        (output / "build_commands.json").write_text(json.dumps(commands, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(name, flush=True)
        with (output / (name + ".log")).open("w", encoding="utf-8") as log:
            subprocess.run(arguments, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)

    execute([sys.executable, "-B", "tools/build_web_frontend.py", "--product-only", "--check"], "frontend")
    execute([sys.executable, "-B", "-m", "PyInstaller", "--distpath", str(output / "dist"),
             "--workpath", str(output / "work"), "packaging/windows/cangoo.spec"], "freeze")
    payload = output / "dist/Cangoo"
    embedded_hooks = frozen_hook_hashes(payload, acceptance_root)
    config = ("#define CANGOO_CLEANUP_ACCEPTANCE 1\n#define CANGOO_CLEANUP_TEST_ROOT LR\"(" + identity["data_root"] + ")\"\n"
              "#define CANGOO_INNO_TEST_ROOT LR\"(" + identity["locations"] + ")\"\n"
              "#define CANGOO_INSTALL_MACHINE_LEAF L\"" + identity["machine_leaf"] + "\"\n"
              if acceptance_root else "#define CANGOO_CLEANUP_PRODUCTION 1\n")
    config_path = output / "native_config.h"
    config_path.write_text(config, encoding="utf-8", newline="\n")
    support = output / "cangoo_inno_support.dll"
    execute([str(compiler), "/nologo", "/std:c++17", "/EHsc", "/W4", "/WX", "/utf-8", "/MT", "/LD",
             "/DUNICODE", "/D_UNICODE", "/DNOMINMAX", "/DWIN32_LEAN_AND_MEAN", "/D_WIN32_WINNT=0x0a00",
             "/FI" + str(config_path), *(str(NATIVE_SOURCE / name) for name in
             ("inno_support.cpp", "install_location.cpp", "user_data_cleanup.cpp")),
             "/Fo" + str(output / "obj") + "/", "/Fe" + str(support), "/link",
             "msi.lib", "shell32.lib", "ole32.lib", "uuid.lib", "advapi32.lib", "wtsapi32.lib", "user32.lib"], "native")
    shutil.copy2(support, payload / "_internal/cangoo_inno_support.dll")
    frozen_hashes = payload_hashes(payload)
    if test_versions and shutil.disk_usage(output).free < sum(path.stat().st_size for path in payload.rglob("*")
                                                             if path.is_file()) * len(versions) * 2:
        raise ValueError("磁盘空间不足以保存独立验收程序与安装包")
    setups = []
    payloads = {}
    for installer_version in versions:
        packaged = acceptance_version_payload(payload, output, installer_version) if test_versions else payload
        manifest, hashes = prepare_manifest(packaged, output / ("manifest_" + installer_version.replace(".", "_")), identity["app_id"])
        payloads[installer_version] = {"directory": str(packaged.relative_to(output)),
                                      "hashes": payload_hashes(packaged), "install_manifest_sha256": sha256(manifest)}
        destination = output / ("installer_" + installer_version.replace(".", "_"))
        destination.mkdir()
        defines = {"AppVersion": installer_version, "AppId": identity["app_id"], "AppName": identity["name"],
                   "ShortcutName": identity["name"], "PayloadDir": str(packaged), "ManifestFile": str(manifest),
                   "PayloadHashesFile": str(hashes), "SupportDll": str(support), "SupportHash": sha256(support),
                   "OutputDir": str(destination)}
        if acceptance_root:
            defines.update(CandidateRoot=identity["locations"], CandidateDefaultDir=identity["default_directory"],
                           MachineLeaf=identity["machine_leaf"])
        execute([str(iscc), *("/D" + key + "=" + value for key, value in defines.items()),
                 str(INNO_SOURCE / "cangoo.iss")], "inno_" + installer_version.replace(".", "_"))
        setup = destination / f"cangoo-{installer_version}-windows-x64-setup.exe"
        if not setup.is_file():
            raise ValueError("Inno 未生成预期安装器")
        setups.append(setup)
    after = source_hashes()
    if before != after or (test_versions and frozen_hashes != payload_hashes(payload)) or any(
            item["hashes"] != payload_hashes(output / item["directory"]) for item in payloads.values()) or legal != {
            name: sha256(WORKSPACE / name) for name in legal}:
        raise ValueError("构建期间源码、许可或程序输入变化，不能使用该候选")
    record = {"schema": 1, "engine": "inno", "arch": "x64", "product_source_version": version,
              "installer_versions": list(versions), "test_version_override": bool(test_versions),
              "identity": identity, "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
              "source_hashes_before": before, "source_hashes_after": after, "license_hashes": legal,
              "frozen_payload_hashes": frozen_hashes, "payloads": payloads,
              "runtime_hook": {"source_sha256": sha256(hook), "embedded_sha256": embedded_hooks,
                               "fixed_root": str(acceptance_root)} if hook else None,
              "tools": {"inno": tool_lock, "iscc_sha256": sha256(iscc), "compiler_sha256": sha256(compiler)},
              "inno_license_sha256": sha256(inno_license),
              "outputs": {str(path.relative_to(output)): sha256(path) for path in setups}, "execution": "build_only"}
    (output / "installer_build_record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("本地候选已生成：" + str(output), flush=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="源码外的全新构建目录")
    parser.add_argument("--iscc", type=Path, required=True, help="已核官方来源的 Inno 7.1 ISCC.exe")
    parser.add_argument("--compiler", type=Path, required=True, help="已配置 x64 INCLUDE/LIB 的 MSVC cl.exe")
    parser.add_argument("--acceptance-root", type=Path, help="编译固定隔离根与独立安装身份")
    parser.add_argument("--test-version", action="append", default=[], help="仅隔离验收可覆盖安装器版本，可重复")
    args = parser.parse_args()
    if Path(sys.prefix).resolve() != (WORKSPACE / ".venv").resolve():
        parser.error("请使用项目 .venv/Scripts/python.exe 执行")
    try:
        build(args.output, args.iscc, args.compiler, acceptance_root=args.acceptance_root,
              test_versions=tuple(args.test_version))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
