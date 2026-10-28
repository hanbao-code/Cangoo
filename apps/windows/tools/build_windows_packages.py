"""一条命令生成本地Windows安装候选、便携ZIP和SHA-256校验值。"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1] if ROOT.name == "windows" and ROOT.parent.name == "apps" else ROOT
sys.path.insert(0, str(ROOT))

from desktop.runtime_paths import PORTABLE_MARKER_CONTENT, PORTABLE_MARKER_NAME
from tools.build_windows_installer import read_product_version, msi_version, write_manifest, verify_toolchain
from tools.work_root import ProjectWorkRoot


def write_portable(payload: Path, target: Path) -> None:
    """将已经过程序清单校验的干净目录封装；模式标记只写入ZIP。"""
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for source in sorted(payload.rglob("*")):
            if source.is_file():
                archive.write(source, "Cangoo/" + source.relative_to(payload).as_posix())
        archive.writestr("Cangoo/" + PORTABLE_MARKER_NAME, PORTABLE_MARKER_CONTENT)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_wix_source_archive(path: Path) -> str:
    """对应源码是发行内容；不能用一个来源链接替代实际交付。"""
    lock = json.loads((ROOT / "packaging/windows/msi/tool_lock.json").read_text(encoding="utf-8"))
    source = lock.get("source_archive", {})
    if source.get("commit") != lock["wix_commit"] or not source.get("filename") or sha256(path) != source.get("sha256"):
        raise ValueError("WiX对应源码归档与固定提交/摘要不符")
    if Path(source["filename"]).name != source["filename"]:
        raise ValueError("对应源码归档名称必须是单一文件名")
    return source["filename"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=WORKSPACE / "dist",
                        help="成品根目录，默认项目内dist")
    parser.add_argument("--toolchain", type=Path, help="旧MSI构建使用的独立WiX工具根")
    parser.add_argument("--wix-source-archive", type=Path, help="旧MSI构建使用的WiX对应源码归档")
    parser.add_argument("--compiler", type=Path, help="已配置x64环境的MSVC cl.exe")
    parser.add_argument("--accept-wix-eula", action="store_true", help="已核对WiX官方二进制维护协议")
    parser.add_argument("--iscc", type=Path, help="Inno构建使用的固定ISCC.exe；与WiX参数互斥")
    args = parser.parse_args()
    if Path(sys.prefix).resolve() != (WORKSPACE / ".venv").resolve():
        parser.error("请使用项目 .venv/Scripts/python.exe 执行")
    try:
        version = read_product_version()[0]
        if args.iscc:
            if args.toolchain or args.wix_source_archive or args.accept_wix_eula:
                raise ValueError("Inno与WiX构建参数不能混用")
            from tools.build_windows_inno import verify_inno_toolchain
            verify_inno_toolchain(args.iscc.resolve(strict=True))
        else:
            version = msi_version(version)
        if not args.iscc and not args.accept_wix_eula:
            raise ValueError("请核对WiX维护协议并显式指定 --accept-wix-eula")
        if not args.iscc:
            if not args.toolchain or not args.wix_source_archive:
                raise ValueError("请选择 --iscc，或完整提供旧WiX工具链及源码归档")
            toolchain = args.toolchain.resolve(strict=True)
            verify_toolchain(toolchain)
            source_archive_name = verify_wix_source_archive(args.wix_source_archive)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    work = ProjectWorkRoot.resolve()
    compiler = Path(args.compiler or shutil.which("cl.exe") or "").resolve()
    if not compiler.is_file():
        parser.error("找不到MSVC；请先配置x64 INCLUDE/LIB并通过 --compiler 指定cl.exe")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    run = work.create_run("windows-packages-" + stamp, owner="tools.build_windows_packages")
    print(f"构建工作目录：{run.path}", flush=True)
    destination = args.output.resolve() / f"{version}_{stamp}"
    staging = destination.with_name(".building-" + destination.name)
    # 仅隔离构建临时文件，不启动产品或加载用户状态。
    env = {**os.environ, "TEMP": str(run.path / "temp"), "TMP": str(run.path / "temp"),
           "PYINSTALLER_CONFIG_DIR": str(run.path / "cache"),
           "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("CANGOO_ACCEPTANCE_RUNTIME_HOOK", None)

    def execute(arguments: list[str], log_name: str) -> None:
        print(log_name, flush=True)
        with (run.path / log_name).open("w", encoding="utf-8") as log:
            subprocess.run([sys.executable, "-B", *arguments], cwd=ROOT, env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True)

    try:
        if args.iscc:
            execute(["tools/build_windows_inno.py", "--output", str(run.path / "inno"),
                     "--iscc", str(args.iscc.resolve()), "--compiler", str(compiler)], "inno.log")
            payload = run.path / "inno/dist/Cangoo"
            installer = run.path / "inno" / ("installer_" + version.replace(".", "_"))
            record = run.path / "inno/installer_build_record.json"
        else:
            execute(["tools/build_web_frontend.py", "--product-only", "--check"], "frontend.log")
            execute(["-m", "PyInstaller", "--distpath", str(run.path / "dist"),
                     "--workpath", str(run.path / "work"),
                     "packaging/windows/cangoo.spec"], "freeze.log")
            payload = run.path / "dist/Cangoo"
            write_manifest(payload, run.path / "manifest")
            execute(["tools/build_windows_installer.py", "--payload", str(payload),
                     "--output", str(run.path / "installer"), "--compiler", str(compiler),
                     "--toolchain", str(toolchain), "--accept-wix-eula"],
                    "installer.log")
            installer = run.path / "installer"
            record = installer / "installer_build_record.json"
        artifacts = run.path / "artifacts"
        artifacts.mkdir()
        setup_name = f"cangoo-{version}-windows-x64-setup.exe"
        shutil.copy2(installer / setup_name, artifacts / setup_name)
        shutil.copy2(record, artifacts / "installer_build_record.json")
        if args.iscc:
            shutil.copy2(run.path / "inno/third_party/inno_license.txt", artifacts / "inno_license.txt")
        else:
            shutil.copy2(args.wix_source_archive, artifacts / source_archive_name)
            verify_wix_source_archive(artifacts / source_archive_name)
        portable = artifacts / f"cangoo-{version}-windows-x64-portable.zip"
        write_portable(payload, portable)
        with zipfile.ZipFile(portable) as archive:
            if archive.testzip() is not None:
                raise ValueError("便携ZIP完整性检查失败")
        files = sorted(artifacts.iterdir())
        (artifacts / "sha256sums.txt").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in files),
            encoding="ascii", newline="\n")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(artifacts, staging)
        for path in artifacts.iterdir():
            if sha256(path) != sha256(staging / path.name):
                raise ValueError("成品复制校验失败")
        staging.rename(destination)
    except (Exception, KeyboardInterrupt):
        print(f"构建失败，保留诊断目录：{run.path}", file=sys.stderr)
        if staging.exists():
            print(f"未完成的成品目录：{staging}", file=sys.stderr)
        raise
    print(f"本地候选已生成：{destination}", flush=True)
    try:
        run.cleanup_success()
    except (OSError, RuntimeError) as error:
        print(f"成品已生成，但临时目录清理失败：{run.path}（{error}）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
