"""使用固定 WiX 工具链将冻结程序封装为 MSI 和标准 Burn 安装器。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import os
from pathlib import Path
import subprocess
import json
import re
import shutil
import sys
import uuid
import zipfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1] if ROOT.name == "windows" and ROOT.parent.name == "apps" else ROOT
APP_ID = "hanbao-code.Cangoo"
MSI_UPGRADE_CODE = "{91633B47-721D-5FB4-85E9-3B45F90CB0D3}"
BUNDLE_UPGRADE_CODE = "{02700CB1-8C18-5410-A739-1F88891FBE17}"
MSI_SOURCE = Path("packaging/windows/msi")
NATIVE_SOURCE = Path("packaging/windows/native")


def read_product_version() -> tuple[str, tuple[int, int, int, int]]:
    """从产品真源读取稳定版本，并核对 Windows 文件版本的数值范围。"""
    content = json.loads((ROOT / "desktop/frontend/assets/help/content.json").read_text(encoding="utf-8"))
    version = content.get("version") if isinstance(content, dict) else None
    if type(version) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]{0,4})(?:\.(?:0|[1-9][0-9]{0,4})){2}", version):
        raise ValueError("软件版本须为规范的三段稳定版，例如1.1.0")
    numbers = tuple(int(part) for part in version.split("."))
    if any(part > 65535 for part in numbers):
        raise ValueError("Windows文件版本的每段数值不能超过65535")
    return version, (*numbers, 0)


def write_manifest(payload: Path, output: Path, app_id: str = APP_ID) -> Path:
    """只登记程序拥有的文件，拒绝混入测试数据或重解析点。"""
    allowed = {"Cangoo.exe", "cangoo_strength_worker.exe", "_internal"}
    if {path.name for path in payload.iterdir()} != allowed:
        raise ValueError("候选目录必须仅包含两个程序和 _internal；不能包含用户数据")

    def program_files(path):
        if path.lstat().st_file_attributes & 0x400:
            raise ValueError("候选目录不能包含重解析点")
        if path.is_dir():
            for child in sorted(path.iterdir()):
                yield from program_files(child)
        elif path.is_file():
            yield path
        else:
            raise ValueError("候选目录含非普通文件")

    names = []
    for path in program_files(payload):
        if path.suffix.lower() in {".db", ".log", ".bak"}:
            raise ValueError("候选目录含非程序数据")
        name = str(path.relative_to(payload))
        if any(character in name for character in "\r\n|") or ".." in name:
            raise ValueError("程序相对路径无效")
        names.append(name)
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "install_files.txt"
    manifest.write_text("\n".join([f"CANGOO-FILES-1 {app_id}", *names]) + "\n",
                        encoding="utf-8-sig", newline="\n")
    return manifest


def digest_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    return digest_file(path, "sha256")


def msi_version(version: str) -> str:
    """MSI 的前三段是实际升级身份，不能沿用较宽的 PE 文件版本上限。"""
    if not re.fullmatch(r"(?:0|[1-9][0-9]{0,4})(?:\.(?:0|[1-9][0-9]{0,4})){2}", version):
        raise ValueError("MSI 版本须为规范的三段稳定版")
    major, minor, build = map(int, version.split("."))
    if major > 255 or minor > 255 or build > 65535:
        raise ValueError("MSI 版本前两段不能超过255，第三段不能超过65535")
    return version


def installer_source_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """构建与源码导出共用的权威安装源码集合，返回 Windows 工程相对路径。"""
    fixed = {Path("tools/build_windows_installer.py"), Path("tools/build_windows_packages.py"),
             Path("tools/qt_bluetooth_build.py"), Path("packaging/windows/cangoo.spec"),
             Path("packaging/windows/qt_bluetooth_lock.json"), Path("packaging/windows/qt_bluetooth_build.md"),
             Path("packaging/windows/qt_bluetooth_6_9_3.patch"),
             Path("packaging/windows/third_party_sources.md"),
             Path("desktop/runtime_paths.py"),
             Path("resources/icons/cangoo/app.ico"), Path("resources/icons/cangoo/app_64.png")}
    for directory in (MSI_SOURCE, NATIVE_SOURCE):
        for path in sorted((root / directory).rglob("*")):
            if path.is_file():
                if path.is_symlink() or path.lstat().st_file_attributes & 0x400:
                    raise ValueError("安装源码不能含重解析点")
                fixed.add(path.relative_to(root))
    return tuple(sorted(fixed))


def source_hashes(root: Path = ROOT) -> dict[str, str]:
    return {str(path.as_posix()): sha256(root / path) for path in installer_source_paths(root)}


def license_hashes() -> dict[str, str]:
    return {name: sha256(WORKSPACE / name) for name in ("LICENSE.md", "COPYING", "OPENSSL_EXCEPTION.md")}


def verify_toolchain(toolchain: Path) -> dict:
    """核原始官方归档和实际解包字节，不下载、不接受协议、不全局安装。"""
    lock = json.loads((ROOT / MSI_SOURCE / "tool_lock.json").read_text(encoding="utf-8"))
    actual = {}
    for item in [lock["runtime"], *lock["packages"]]:
        archive_path = toolchain / item["archive"]
        if digest_file(archive_path, "sha512") != item["sha512"]:
            raise ValueError("工具归档摘要不符：" + item["archive"])
        directory = (toolchain / item["directory"]).resolve(strict=True)
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                target = directory / member.filename
                if not target.resolve(strict=True).is_relative_to(directory) or target.is_symlink():
                    raise ValueError("工具归档路径越界")
                digest = hashlib.sha256(archive.read(member)).hexdigest()
                if sha256(target) != digest:
                    raise ValueError("实际工具字节不符：" + member.filename)
        actual[item["archive"]] = item["sha512"]
    return {"wix_version": lock["wix_version"], "wix_commit": lock["wix_commit"],
            "runtime_version": lock["runtime_version"], "archives_sha512": actual}


def build_environment(toolchain: Path, output: Path) -> dict[str, str]:
    """仅隔离构建工具的缓存；该环境不能拿来充当产品资料的隔离边界。"""
    env = dict(os.environ)
    for name in ("CL", "_CL_"):
        env.pop(name, None)
    directories = {"DOTNET_CLI_HOME": "dotnet_home", "NUGET_PACKAGES": "nuget",
                   "NUGET_HTTP_CACHE_PATH": "nuget_http", "NUGET_PLUGINS_CACHE_PATH": "nuget_plugins",
                   "NUGET_SCRATCH": "nuget_scratch", "TEMP": "temp", "TMP": "temp",
                   "TMPDIR": "temp", "APPDATA": "roaming", "LOCALAPPDATA": "local", "USERPROFILE": "profile"}
    for name, relative in directories.items():
        directory = output / "build_environment" / relative
        directory.mkdir(parents=True, exist_ok=True)
        env[name] = str(directory)
    env.update(DOTNET_ROOT=str(toolchain / "net10/runtime"), DOTNET_ROOT_X64=str(toolchain / "net10/runtime"),
               DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1",
               DOTNET_NOLOGO="1", DOTNET_MULTILEVEL_LOOKUP="0", DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE="1",
               DOTNET_GENERATE_ASPNET_CERTIFICATE="false", DOTNET_ADD_GLOBAL_TOOLS_TO_PATH="false")
    includes = env.get("INCLUDE", "").split(os.pathsep)
    for item in tuple(includes):
        shared = Path(item).parent / "shared"
        if Path(item).name.lower() == "um" and shared.is_dir() and str(shared) not in includes:
            includes.append(str(shared))
    env["INCLUDE"] = os.pathsep.join(includes)
    return env


def validate_acceptance(value: dict | None) -> dict:
    """隔离身份及删除根只能在编译时明确指定，生产没有路径参数。"""
    if value is None:
        return {"name": "小仓", "msi_upgrade_code": MSI_UPGRADE_CODE,
                "bundle_upgrade_code": BUNDLE_UPGRADE_CODE}
    if set(value) != {"name", "msi_upgrade_code", "bundle_upgrade_code", "cleanup_root", "install_directory"}:
        raise ValueError("隔离安装配置字段不完整或含未知字段")
    if not re.fullmatch(r"小仓·验收-[a-f0-9]{8}", value["name"]):
        raise ValueError("隔离安装名称必须带唯一短ID")
    for key, production in (("msi_upgrade_code", MSI_UPGRADE_CODE), ("bundle_upgrade_code", BUNDLE_UPGRADE_CODE)):
        if str(uuid.UUID(value[key])).lower() == str(uuid.UUID(production)).lower():
            raise ValueError("隔离安装不得复用正式身份")
    work = Path("D:/pycharm/Password_manager_work").resolve(strict=True)
    for key in ("cleanup_root", "install_directory"):
        path = Path(value[key]).absolute()
        allowed = path.resolve().is_relative_to(work) and path.resolve() != work
        if key == "install_directory" and not allowed:
            programs = current_user_programs_directory()
            allowed = path.parent.resolve() == programs.resolve() and bool(re.fullmatch(r"CangooMsiAcceptance_[a-f0-9]{8}", path.name))
        if not allowed or any(c in str(path) for c in '"\r\n'):
            raise ValueError("清理根必须在D盘工作根；程序目录仅允许该根或当前用户Programs下的唯一验收目录")
        value[key] = str(path)
    return value


def current_user_programs_directory() -> Path:
    """复用既有 Win32 路径端口，只查询系统位置，不信任隔离环境变量。"""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from desktop.runtime_paths import _known_folder
    return _known_folder("F1B32785-6FBA-4FCF-9D55-7B8E7F157091") / "Programs"


def build_installer(payload: Path, output: Path, toolchain: Path, *, version: str | None = None,
                    acceptance: dict | None = None, compiler: Path | None = None) -> Path:
    """只构建，不运行安装器；MSI、辅助库和完整构建记录保存在输出目录。"""
    version = msi_version(version or read_product_version()[0])
    identity = validate_acceptance(dict(acceptance) if acceptance else None)
    identity["msi_product_code"] = "{" + str(uuid.uuid5(uuid.UUID(identity["msi_upgrade_code"]), version)).upper() + "}"
    payload = payload.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output == payload or payload in output.parents:
        raise ValueError("安装输出必须是程序目录外的全新目录")
    before, legal_before = source_hashes(), license_hashes()
    tools = verify_toolchain(toolchain)
    compiler = compiler or Path(shutil.which("cl.exe") or "")
    if not compiler.is_file():
        raise ValueError("需要已配置x64 INCLUDE/LIB的MSVC cl.exe")
    output.mkdir(parents=True)
    write_manifest(payload, output)
    payload_hashes = {path.relative_to(payload).as_posix(): sha256(path)
                      for path in sorted(payload.rglob("*")) if path.is_file()}
    env = build_environment(toolchain, output)
    commands = []
    started = datetime.now(timezone.utc).isoformat()

    def execute(arguments: list[str], name: str) -> None:
        commands.append(arguments)
        (output / "build_commands.json").write_text(json.dumps(commands, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        with (output / (name + ".log")).open("w", encoding="utf-8") as log:
            subprocess.run(arguments, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)

    packages = toolchain / "packages"
    function_api = packages / "wixtoolset.wixstandardbootstrapperapplicationfunctionapi/7.0.0"
    bootstrap_api = packages / "wixtoolset.bootstrapperapplicationapi/7.0.0"
    dutil = packages / "wixtoolset.dutil/7.0.0"
    (output / "obj").mkdir()
    config = '#define CANGOO_MSI_UPGRADE_CODE L"' + identity["msi_upgrade_code"] + '"\n'
    if acceptance:
        config += '#define CANGOO_CLEANUP_ACCEPTANCE 1\n#define CANGOO_CLEANUP_TEST_ROOT LR"(' + identity["cleanup_root"] + ')"\n'
        config += '#define CANGOO_INSTALL_TEST_ROOT LR"(' + identity["install_directory"] + ')"\n'
    else:
        config += "#define CANGOO_CLEANUP_PRODUCTION 1\n"
    (output / "native_config.h").write_text(config, encoding="utf-8", newline="\n")
    native_sources = [ROOT / NATIVE_SOURCE / name for name in
                      ("cangoo_ba_functions.cpp", "user_data_cleanup.cpp", "install_location.cpp")]
    execute([str(compiler), "/nologo", "/std:c++17", "/EHsc", "/W4", "/WX", "/utf-8", "/MT", "/LD",
             "/DUNICODE", "/D_UNICODE", "/DNOMINMAX", "/DWIN32_LEAN_AND_MEAN", "/D_WIN32_WINNT=0x0a00",
             "/FI" + str(output / "native_config.h"), "/I" + str(function_api / "lib/native/include"),
             "/I" + str(bootstrap_api / "build/native/include"), "/I" + str(dutil / "build/native/include"),
             *(str(path) for path in native_sources), "/Fo" + str(output / "obj") + "/",
             "/Fe" + str(output / "cangoo_ba_functions.dll"), "/link",
             str(function_api / "lib/native/v14/x64/wixstdfn.lib"),
             "advapi32.lib", "wtsapi32.lib", "shell32.lib", "ole32.lib", "uuid.lib", "user32.lib", "comctl32.lib", "msi.lib"], "native")

    legal_paths = {name: WORKSPACE / name for name in legal_before}
    legal_paths.update({"Installer helper — MIT": ROOT / NATIVE_SOURCE / "LICENSE",
                        "WiX Toolset — MS-RL": ROOT / MSI_SOURCE / "third_party/wix_license.txt"})
    documents = "".join('<h2>' + html.escape(name) + '</h2><pre>' +
                        html.escape(path.read_text(encoding="utf-8")) + '</pre>'
                        for name, path in legal_paths.items())
    (output / "license.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>小仓 · Cangoo</title><style>body{max-width:56rem;margin:3rem auto;padding:0 1.5rem;font:16px/1.65 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}</style>' + documents + '</html>', encoding="utf-8", newline="\n")
    wix = [str(toolchain / "net10/runtime/dotnet.exe"), "--fx-version", "10.0.13",
           str(packages / "wix/7.0.0/tools/net8.0/any/wix.dll")]
    defines = {"ProductVersion": version, "ProductName": identity["name"], "ProductCode": identity["msi_product_code"],
               "UpgradeCode": identity["msi_upgrade_code"], "BundleUpgradeCode": identity["bundle_upgrade_code"],
               "PayloadDir": str(payload), "AppIcon": str(ROOT / "resources/icons/cangoo/app.ico"),
               "AppLogo": str(ROOT / "resources/icons/cangoo/app_64.png"),
               "SourceDir": str(ROOT / MSI_SOURCE), "BuildDir": str(output)}
    if acceptance:
        defines["AcceptanceInstallDir"] = identity["install_directory"]
        identity["component_guid_seed"] = "{" + str(uuid.uuid5(uuid.UUID(identity["msi_upgrade_code"]),
            os.path.normcase(str(Path(identity["install_directory"]).resolve())))).upper() + "}"
        defines["AcceptanceComponentGuidSeed"] = identity["component_guid_seed"]
    flags = [argument for key, value in defines.items() for argument in ("-d", key + "=" + value)]
    execute([*wix, "build", "-acceptEula", "wix7", "-arch", "x64", *flags,
             str(ROOT / MSI_SOURCE / "package.wxs"), "-o", str(output / "cangoo.msi")], "msi")
    setup = output / f"cangoo-{version}-windows-x64-setup.exe"
    extension = packages / "wixtoolset.bootstrapperapplications.wixext/7.0.0/wixext7/WixToolset.BootstrapperApplications.wixext.dll"
    execute([*wix, "build", "-acceptEula", "wix7", "-arch", "x64", "-ext", str(extension), *flags,
             str(ROOT / MSI_SOURCE / "bundle.wxs"), "-o", str(setup)], "bundle")
    execute([*wix, "burn", "extract", "-acceptEula", "wix7", str(setup), "-o", str(output / "extracted"),
             "-oba", str(output / "extracted_ba")], "inspect")
    embedded = list((output / "extracted").rglob("cangoo.msi"))
    if len(embedded) != 1 or sha256(embedded[0]) != sha256(output / "cangoo.msi"):
        raise ValueError("Bundle 中的 MSI 与本轮产物不一致")
    if sha256(output / "extracted_ba/cangoo_ba_functions.dll") != sha256(output / "cangoo_ba_functions.dll"):
        raise ValueError("Bundle 中的原生辅助库与本轮产物不一致")
    registration = ET.parse(output / "extracted_ba/manifest.xml").find("{*}Registration")
    if registration is None or registration.get("Scope") != "perUserOrMachine":
        raise ValueError("Bundle 安装范围与模板不一致")
    identity["bundle_registration_code"] = registration.attrib["Code"]
    identity["scope"] = registration.attrib["Scope"]
    after, legal_after = source_hashes(), license_hashes()
    if before != after or legal_before != legal_after:
        raise ValueError("构建期间安装源码或许可发生变化，不能使用该候选")
    if payload_hashes != {path.relative_to(payload).as_posix(): sha256(path)
                          for path in sorted(payload.rglob("*")) if path.is_file()}:
        raise ValueError("构建期间程序输入发生变化")
    record = {"schema": 1, "engine": "wix7", "version": version, "arch": "x64", "identity": identity,
              "acceptance": acceptance, "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
              "source_hashes_before": before, "source_hashes_after": after,
              "license_hashes_before": legal_before, "license_hashes_after": legal_after,
              "payload_hashes": payload_hashes, "tools": {**tools, "compiler_sha256": sha256(compiler)},
              "outputs": {path.name: sha256(path) for path in (setup, output / "cangoo.msi", output / "cangoo_ba_functions.dll")},
              "embedded_msi_sha256": sha256(embedded[0]),
              "embedded_ba_functions_sha256": sha256(output / "extracted_ba/cangoo_ba_functions.dll"),
              "execution": "build_only"}
    (output / "installer_build_record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return setup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--toolchain", type=Path, required=True, help="已按tool_lock.json准备的独立工具根")
    parser.add_argument("--compiler", type=Path, help="x64 MSVC cl.exe；默认使用PATH中的cl.exe")
    parser.add_argument("--accept-wix-eula", action="store_true", help="已核对本次构建适用WiX官方二进制维护协议")
    parser.add_argument("--acceptance-config", type=Path, help="仅编译固定公开隔离根与独立身份")
    args = parser.parse_args()
    try:
        version = msi_version(read_product_version()[0])
        if not args.accept_wix_eula:
            raise ValueError("请先核对WiX维护协议，再显式指定 --accept-wix-eula")
        acceptance = json.loads(args.acceptance_config.read_text(encoding="utf-8")) if args.acceptance_config else None
        build_installer(args.payload, args.output, args.toolchain.resolve(strict=True), version=version,
                        acceptance=acceptance, compiler=args.compiler)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
