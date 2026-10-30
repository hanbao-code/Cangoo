"""原生数据库目标选择及单次文件访问能力。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QWidget,
)

from desktop.runtime_paths import RuntimePaths


class DatabaseTargetKind(str, Enum):
    OPEN_EXISTING = "OPEN_EXISTING"
    CREATE_NEW = "CREATE_NEW"


@dataclass(frozen=True, slots=True)
class DatabaseTarget:
    path: Path
    kind: DatabaseTargetKind


class DatabaseTargetSelector(Protocol):
    def choose(self) -> DatabaseTarget | None:
        """Run one fixed native target-selection task."""


class NativeDatabaseTargetSelector:
    """Choose one final path, then classify it under native authority."""

    def __init__(
        self,
        parent: QWidget,
        isolation: RuntimePaths,
    ) -> None:
        self._parent = parent
        self._isolation = isolation
        self._language = "ZH"

    def set_language(self, language: str) -> None:
        """Project the validated host language into the native dialog."""

        normalized = str(language).upper()
        if normalized not in {"ZH", "EN"}:
            raise ValueError("database target language must be ZH or EN")
        self._language = normalized

    def choose(self) -> DatabaseTarget | None:
        chooser = QFileDialog(self._parent)
        chooser.setWindowTitle(
            "选择密码数据库"
            if self._language == "ZH"
            else "Select password database"
        )
        chooser.setDirectory(
            str(self._isolation.database_chooser_directory)
        )
        chooser.setNameFilter(self._isolation.database_name_filter)
        default_suffix = self._isolation.database_default_suffix
        if default_suffix:
            chooser.setDefaultSuffix(default_suffix)
        chooser.setFileMode(QFileDialog.FileMode.AnyFile)
        chooser.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        chooser.setLabelText(
            QFileDialog.DialogLabel.Accept,
            "选择" if self._language == "ZH" else "Select",
        )
        chooser.selectFile("pdm.db")
        if chooser.exec() != QDialog.DialogCode.Accepted:
            return None
        selected = chooser.selectedFiles()
        if len(selected) != 1:
            return None
        return self._bounded_target(selected[0])

    def _bounded_target(
        self,
        value: str,
    ) -> DatabaseTarget | None:
        if not value:
            return None
        path = Path(value)
        if not self._isolation.database_candidate_syntax_is_safe(path):
            return None
        path = self._isolation.normalize_database_candidate(path)
        exists = path.exists()
        if exists and not self._isolation.allows_existing_database(path):
            return None
        if not exists and not self._isolation.allows_new_database(path):
            return None
        return DatabaseTarget(
            path=path,
            kind=(
                DatabaseTargetKind.OPEN_EXISTING
                if exists
                else DatabaseTargetKind.CREATE_NEW
            ),
        )


__all__ = [
    "DatabaseTarget",
    "DatabaseTargetKind",
    "DatabaseTargetSelector",
    "NativeDatabaseTargetSelector",
]
