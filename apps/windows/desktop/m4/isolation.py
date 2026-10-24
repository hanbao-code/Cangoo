"""Validated temporary-state boundary for M4 candidate execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from desktop.runtime_paths import database_candidate_syntax_is_safe


ISOLATION_MARKER_NAME = ".pdm-m4-isolated-v1"
ISOLATION_MARKER_CONTENT = (
    "Password Manager M4 isolated acceptance root\n"
)


class M4IsolationError(RuntimeError):
    """The requested M4 root is not an explicitly prepared isolation root."""


@dataclass(frozen=True, slots=True)
class M4IsolationPaths:
    """All mutable M4.1 state, rooted below one validated directory."""

    root: Path
    settings_file: Path
    security_file: Path
    database_root: Path

    @classmethod
    def from_root(cls, root: Path) -> "M4IsolationPaths":
        if not isinstance(root, Path):
            raise TypeError("M4 isolation root must be a Path")
        try:
            resolved = root.resolve(strict=True)
        except OSError as exc:
            raise M4IsolationError(
                "M4 isolation root is missing or unreadable"
            ) from exc
        if not resolved.is_dir():
            raise M4IsolationError("M4 isolation root is not a directory")

        marker = resolved / ISOLATION_MARKER_NAME
        try:
            marker_content = marker.read_text(encoding="utf-8")
        except OSError as exc:
            raise M4IsolationError(
                "M4 isolation marker is missing or unreadable"
            ) from exc
        if marker_content != ISOLATION_MARKER_CONTENT:
            raise M4IsolationError("M4 isolation marker is invalid")

        settings_dir = resolved / "config"
        security_dir = resolved / "state"
        database_root = resolved / "databases"
        for directory in (
            settings_dir,
            security_dir,
            database_root,
        ):
            directory.mkdir(parents=False, exist_ok=True)
            if (
                not directory.is_dir()
                or directory.resolve(strict=True).parent != resolved
            ):
                raise M4IsolationError(
                    "M4 isolation child directory escaped its root"
                )

        return cls(
            root=resolved,
            settings_file=settings_dir / "settings.json",
            security_file=security_dir / "security.st",
            database_root=database_root,
        )

    def contains_database_target(self, path: Path) -> bool:
        """Accept only direct ``.db`` children of the isolated DB directory."""

        if not isinstance(path, Path):
            return False
        try:
            resolved = path.resolve(strict=False)
            parent = resolved.parent.resolve(strict=True)
        except OSError:
            return False
        return (
            parent == self.database_root
            and resolved.suffix.lower() == ".db"
            and resolved.name not in {"", ".", ".."}
        )

    @property
    def default_database(self) -> Path:
        return self.database_root / "pdm.db"

    @property
    def database_chooser_directory(self) -> Path:
        return self.database_root

    @property
    def database_name_filter(self) -> str:
        return "Password database (*.db)"

    @property
    def database_default_suffix(self) -> str:
        return "db"

    def database_candidate_syntax_is_safe(self, path: Path) -> bool:
        return database_candidate_syntax_is_safe(path)

    def normalize_database_candidate(self, path: Path) -> Path:
        """保留 M4 固定根和缺失后缀补 ``.db`` 的原行为。"""

        if path.suffix == "":
            path = path.with_suffix(".db")
        return path.resolve(strict=False)

    def allows_existing_database(self, path: Path) -> bool:
        if not self.database_candidate_syntax_is_safe(path):
            return False
        return self.contains_database_target(path) and path.is_file()

    def allows_new_database(self, path: Path) -> bool:
        if not self.database_candidate_syntax_is_safe(path):
            return False
        return self.contains_database_target(path) and not path.exists()

    def allows_recovery_snapshot(self, path: Path) -> bool:
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            return False
        return resolved.parent == self.database_root and resolved.is_file()


__all__ = [
    "ISOLATION_MARKER_CONTENT",
    "ISOLATION_MARKER_NAME",
    "M4IsolationError",
    "M4IsolationPaths",
]
