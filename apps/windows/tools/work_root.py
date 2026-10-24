"""统一的项目外运行目录；只清理当前带归属标记的 run。"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WORK_ROOT = Path(r"D:\pycharm\Password_manager_work")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
OWNER_MARKER = ".pdm-run-owner.json"


@dataclass(frozen=True, slots=True)
class ProjectWorkRoot:
    root: Path
    temporary: Path
    acceptance_results: Path
    build_outputs: Path

    @classmethod
    def resolve(cls, override: Path | None = None) -> "ProjectWorkRoot":
        configured = override
        if configured is None:
            value = os.environ.get("PDM_WORK_ROOT", "").strip()
            configured = Path(value) if value else DEFAULT_WORK_ROOT
        root = configured.resolve(strict=False)
        return cls(
            root=root,
            temporary=root / "临时运行",
            acceptance_results=root / "验收结果",
            build_outputs=root / "构建输出",
        )

    def prepare(self) -> None:
        for directory in (
            self.root,
            self.temporary,
            self.acceptance_results,
            self.build_outputs,
        ):
            directory.mkdir(parents=True, exist_ok=True)
            if not directory.is_dir():
                raise RuntimeError("WORK_ROOT_DIRECTORY_INVALID")

    def create_run(self, run_id: str, *, owner: str) -> "OwnedRunDirectory":
        if not RUN_ID.fullmatch(run_id):
            raise ValueError("run_id must use bounded ASCII characters")
        self.prepare()
        path = (self.temporary / run_id).resolve(strict=False)
        if path.parent != self.temporary.resolve(strict=True):
            raise RuntimeError("WORK_RUN_ESCAPED_ROOT")
        path.mkdir(parents=False, exist_ok=False)
        marker = {
            "schema_version": 1,
            "run_id": run_id,
            "owner": owner,
            "pid": os.getpid(),
        }
        (path / OWNER_MARKER).write_text(
            json.dumps(marker, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for name in ("temp", "chromium-profile", "data", "config"):
            (path / name).mkdir()
        return OwnedRunDirectory(path=path, marker=marker, root=self)


@dataclass(frozen=True, slots=True)
class OwnedRunDirectory:
    path: Path
    marker: dict[str, object]
    root: ProjectWorkRoot

    def subprocess_environment(self) -> dict[str, str]:
        temp = str(self.path / "temp")
        return {
            "TEMP": temp,
            "TMP": temp,
            "PDM_CHROMIUM_PROFILE_ROOT": str(
                self.path / "chromium-profile"
            ),
            "PDM_TEST_DATA_ROOT": str(self.path / "data"),
            "PDM_TEST_CONFIG_ROOT": str(self.path / "config"),
        }

    def cleanup_success(self) -> None:
        """只删除本对象精确拥有且标记内容仍匹配的目录。"""

        resolved = self.path.resolve(strict=True)
        expected_parent = self.root.temporary.resolve(strict=True)
        if resolved.parent != expected_parent:
            raise RuntimeError("WORK_RUN_CLEANUP_ESCAPED_ROOT")
        marker_path = resolved / OWNER_MARKER
        try:
            actual = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("WORK_RUN_OWNER_MARKER_INVALID") from exc
        if actual != self.marker:
            raise RuntimeError("WORK_RUN_OWNER_MARKER_CHANGED")
        shutil.rmtree(resolved)


__all__ = [
    "DEFAULT_WORK_ROOT",
    "OWNER_MARKER",
    "OwnedRunDirectory",
    "ProjectWorkRoot",
]
