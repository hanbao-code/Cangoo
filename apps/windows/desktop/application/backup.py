"""加密备份的原生文件能力与会话预览状态。"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
from typing import Callable, Protocol

from PySide6.QtWidgets import QDialog, QFileDialog, QWidget

from core.backup import (
    BACKUP_FILE_MAX_BYTES, BACKUP_RECORD_MAX_ITEMS, BackupError,
    backup_identical_note_targets, backup_note_groups,
    backup_password_content, similar_name_key, validate_backup_payload,
)
from desktop.runtime_paths import (
    _is_windows_reparse_point,
    _windows_drive_type,
    database_candidate_syntax_is_safe,
)
from .record_field_reads import (
    CHUNK_CHARACTERS,
    CHUNK_UTF8_BYTES,
    field_is_long,
    field_preview,
)


BACKUP_SUFFIX = ".pdmbackup.json"
BACKUP_TTL_MS = 300_000
BACKUP_FIELD_TTL_MS = 30_000
_MAX_TICKETS = 32
SECRET_FIELDS = frozenset({"PASSWORD", "TOTP", "RECOVERY_CODES"})
BUSINESS_FIELDS = frozenset({"PLATFORM", "ACCOUNT", "PASSWORD", "NOTES", "TOTP", "RECOVERY_CODES", "FAVORITE"})
PASSWORD_FIELDS = ("PLATFORM", "ACCOUNT", "PASSWORD", "NOTES", "TOTP", "RECOVERY_CODES", "FAVORITE", "STRENGTH", "PASSWORD_CHANGED_AT", "UPDATED_AT")
NOTE_FIELDS = ("PLATFORM", "NOTES", "FAVORITE", "CREATED_AT", "UPDATED_AT", "SORT_ORDER")
TEXT_FIELDS = frozenset(PASSWORD_FIELDS + NOTE_FIELDS) - SECRET_FIELDS


class BackupFileSelector(Protocol):
    def choose_destination(self) -> Path | None: ...

    def choose_source(self) -> Path | None: ...


class NullBackupFileSelector:
    def choose_destination(self) -> Path | None:
        return None

    def choose_source(self) -> Path | None:
        return None


class NativeBackupFileSelector:
    """导入显示所有文件，导出仅建议默认备份扩展名。"""

    def __init__(self, parent: QWidget, initial_directory: Path) -> None:
        self._parent = parent
        self._default_parent = parent
        self._initial_directory = initial_directory
        self._language = "ZH"

    def set_parent(self, parent: QWidget | None) -> None:
        self._parent = parent if parent is not None else self._default_parent

    def set_language(self, language: str) -> None:
        normalized = str(language).upper()
        if normalized not in {"ZH", "EN"}:
            raise ValueError("backup selector language must be ZH or EN")
        self._language = normalized

    def choose_destination(self) -> Path | None:
        chooser = self._chooser(
            "选择加密备份保存位置" if self._language == "ZH" else "Save encrypted backup",
            QFileDialog.AcceptMode.AcceptSave,
            QFileDialog.FileMode.AnyFile,
        )
        chooser.setNameFilter("所有文件 (*)" if self._language == "ZH" else "All files (*)")
        chooser.setDefaultSuffix(BACKUP_SUFFIX.lstrip("."))
        chooser.selectFile(f"cangoo{BACKUP_SUFFIX}")
        return self._selected(chooser)

    def choose_source(self) -> Path | None:
        chooser = self._chooser(
            "选择加密备份" if self._language == "ZH" else "Select encrypted backup",
            QFileDialog.AcceptMode.AcceptOpen,
            QFileDialog.FileMode.ExistingFile,
        )
        chooser.setNameFilter("所有文件 (*)" if self._language == "ZH" else "All files (*)")
        return self._selected(chooser)

    def _chooser(self, title: str, accept_mode, file_mode) -> QFileDialog:
        chooser = QFileDialog(self._parent)
        chooser.setWindowTitle(title)
        chooser.setDirectory(str(self._initial_directory))
        chooser.setNameFilter(
            "小仓加密备份 (*.pdmbackup.json)"
            if self._language == "ZH"
            else "Cangoo encrypted backup (*.pdmbackup.json)"
        )
        chooser.setAcceptMode(accept_mode)
        chooser.setFileMode(file_mode)
        return chooser

    @staticmethod
    def _selected(chooser: QFileDialog) -> Path | None:
        if chooser.exec() != QDialog.DialogCode.Accepted:
            return None
        values = chooser.selectedFiles()
        return Path(values[0]) if len(values) == 1 else None


@dataclass(frozen=True, slots=True)
class BackupSelection:
    ticket: str
    kind: str
    path: Path
    identity: tuple[int, int, int, int, int] | None
    page_epoch: int
    session_epoch: int
    expires_at: float


@dataclass(slots=True)
class BackupConflict:
    conflict_id: str
    platform: str
    current: dict[str, object]
    incoming: dict[str, object]
    decision: str = "UNDECIDED"
    kind: str = "PASSWORD"
    source_index: int = -1
    candidates: list[dict[str, object]] = field(default_factory=list)
    target_index: int = 0
    status: str = "CONFLICT"
    target_selected: bool = True


@dataclass(slots=True)
class BackupPreview:
    ticket: str
    page_epoch: int
    session_epoch: int
    source_ticket: str
    source_path: Path | None
    source_identity: tuple[int, int, int, int, int] | None
    source_digest: str
    retry_identity: str
    payload: dict[str, object]
    conflicts: list[BackupConflict]
    note_groups: dict[str, list[dict]] = field(default_factory=dict)
    reserved_note_ids: set[int] = field(default_factory=set)
    received_snapshot: bool = False


@dataclass(frozen=True, slots=True)
class BackupPreviewDraft:
    selection: BackupSelection | None
    digest: str
    payload: dict[str, object]
    current_records: tuple[dict[str, object], ...]
    retry_identity: str
    current_notes: tuple[dict[str, object], ...] = ()


@dataclass(slots=True)
class _BackupRead:
    read_id: str
    binding: tuple[str, str, str, int]
    expires_at: float


class BackupRejected(ValueError):
    pass


@dataclass(slots=True)
class ExportSelection:
    ticket: str
    page_epoch: int
    session_epoch: int
    entries: dict[tuple[str, int], str] = field(default_factory=dict, repr=False)
    previous_ticket: str = ""
    confirmed: bool = False
    generation: int = 0
    query: str = ""
    kind: str = "ALL"
    offset: int = 0
    limit: int = 20
    total: int = 0
    filtered_selected_count: int = 0
    changed_count: int = 0
    items: list[dict[str, object]] = field(default_factory=list, repr=False)

    def info(self) -> dict[str, object]:
        return {"selectionTicket": self.ticket,
                "passwordCount": sum(kind == "PASSWORD" for kind, _ in self.entries),
                "noteCount": sum(kind == "NOTE" for kind, _ in self.entries)}

    def page(self) -> dict[str, object]:
        return {**self.info(), "query": self.query, "kind": self.kind, "offset": self.offset,
                "limit": self.limit, "total": self.total,
                "allSelected": self.total > 0 and self.filtered_selected_count == self.total,
                "changedCount": self.changed_count,
                "items": [{**item, "selected": (item["kind"], item["id"]) in self.entries} for item in self.items]}


class BackupController:
    def __init__(
        self,
        selector: BackupFileSelector,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._selector = selector
        self._clock = clock
        self._selections: dict[str, BackupSelection] = {}
        self._previews: dict[str, BackupPreview] = {}
        self._retry_sources: dict[str, str] = {}
        self._reads: dict[str, _BackupRead] = {}
        self._active_read: tuple[str, int] | None = None
        self._detail: tuple[str, str, int] | None = None
        self._export_selections: dict[str, ExportSelection] = {}

    def begin_export_selection(self, page_epoch: int, session_epoch: int) -> dict[str, object]:
        previous = None
        for value in tuple(self._export_selections.values()):
            if (value.page_epoch, value.session_epoch) == (page_epoch, session_epoch):
                if value.confirmed:
                    previous = value
                else:
                    self._export_selections.pop(value.ticket)
                    value.entries.clear()
                    value.items.clear()
        if len(self._export_selections) >= 8:
            raise BackupRejected("REQUEST_BUSY")
        value = ExportSelection(secrets.token_urlsafe(24), page_epoch, session_epoch,
                                dict(previous.entries) if previous else {}, previous.ticket if previous else "")
        self._export_selections[value.ticket] = value
        return value.info()

    def export_selection(self, ticket: str, page_epoch: int, session_epoch: int, *, draft=False) -> ExportSelection:
        value = self._export_selections.get(ticket)
        if value is None or (value.page_epoch, value.session_epoch) != (page_epoch, session_epoch):
            raise BackupRejected("SELECTION_EXPIRED")
        if draft and value.confirmed:
            raise BackupRejected("INVALID_ARGUMENT")
        return value

    def change_export_selection(self, value: ExportSelection, action: str, kind: str,
                                record_id: int, revision: str) -> dict[str, object]:
        if (value.confirmed or type(action) is not str or type(kind) is not str
                or type(record_id) is not int or type(revision) is not str):
            raise BackupRejected("INVALID_ARGUMENT")
        if action == "CLEAR":
            if kind != "ALL" or record_id or revision:
                raise BackupRejected("INVALID_ARGUMENT")
            value.entries.clear()
            value.filtered_selected_count = 0
        elif action in {"ADD", "REMOVE"}:
            item = next((item for item in value.items if item["kind"] == kind and item["id"] == record_id
                         and item["revision"] == revision), None)
            if item is None:
                raise BackupRejected("REVISION_CONFLICT")
            selected_before = len(value.entries)
            if action == "ADD":
                if (kind, record_id) not in value.entries and len(value.entries) >= BACKUP_RECORD_MAX_ITEMS:
                    raise BackupRejected("REQUEST_TOO_LARGE")
                value.entries[(kind, record_id)] = revision
            else:
                value.entries.pop((kind, record_id), None)
            value.filtered_selected_count += len(value.entries) - selected_before
        else:
            raise BackupRejected("INVALID_ARGUMENT")
        value.generation += 1
        return value.page()

    def finish_export_selection(self, value: ExportSelection, action: str) -> dict[str, object]:
        if action == "CONFIRM":
            if value.confirmed or not value.entries:
                raise BackupRejected("INVALID_ARGUMENT")
            self._export_selections.pop(value.previous_ticket, None)
            value.previous_ticket = ""
            value.confirmed = True
            value.items.clear()
            return value.info()
        if action not in {"CANCEL", "DISCARD"} or action == "CANCEL" and value.confirmed:
            raise BackupRejected("INVALID_ARGUMENT")
        self._export_selections.pop(value.ticket, None)
        previous = self._export_selections.get(value.previous_ticket) if action == "CANCEL" else None
        value.entries.clear()
        value.items.clear()
        return previous.info() if previous else {"selectionTicket": "", "passwordCount": 0, "noteCount": 0}

    def export_choice(self, page_epoch: int, session_epoch: int, scope: str):
        if scope in {"ALL", "PASSWORDS", "NOTES"}:
            return scope, None
        if scope != "CUSTOM":
            raise BackupRejected("INVALID_ARGUMENT")
        value = next((value for value in self._export_selections.values()
                      if value.confirmed and (value.page_epoch, value.session_epoch) == (page_epoch, session_epoch)), None)
        if value is None or not value.entries:
            raise BackupRejected("INVALID_ARGUMENT")
        selection = {kind: {record_id: revision for (entry_kind, record_id), revision in value.entries.items()
                            if entry_kind == kind} for kind in ("PASSWORD", "NOTE")}
        wire_scope = "ALL" if selection["PASSWORD"] and selection["NOTE"] else "PASSWORDS" if selection["PASSWORD"] else "NOTES"
        return wire_scope, selection

    def clear_export_selection(self, page_epoch: int, session_epoch: int | None = None) -> None:
        for value in tuple(self._export_selections.values()):
            if value.page_epoch == page_epoch and (session_epoch is None or value.session_epoch == session_epoch):
                value.entries.clear()
                value.items.clear()
                self._export_selections.pop(value.ticket, None)

    def discard_export_draft(self, ticket: str) -> None:
        value = self._export_selections.get(ticket)
        if value is not None and not value.confirmed:
            self._export_selections.pop(ticket)
            value.entries.clear()
            value.items.clear()

    def choose(self, kind: str, page_epoch: int, session_epoch: int) -> dict[str, object]:
        selected = (
            self._selector.choose_destination()
            if kind == "DESTINATION"
            else self._selector.choose_source()
        )
        return self.mint(kind, selected, page_epoch, session_epoch)

    def mint(
        self,
        kind: str,
        selected: Path | None,
        page_epoch: int,
        session_epoch: int,
    ) -> dict[str, object]:
        if selected is None:
            return self._selection_result(None)
        path = self._normalize(selected, source=kind == "SOURCE")
        identity = file_identity(path)
        if kind == "SOURCE":
            if identity is None:
                raise BackupRejected("NOT_FOUND")
            if identity[2] > BACKUP_FILE_MAX_BYTES:
                raise BackupRejected("BACKUP_LIMIT_EXCEEDED")
        elif path.exists() and identity is None:
            raise BackupRejected("INVALID_ARGUMENT")
        ticket = secrets.token_urlsafe(24)
        selection = BackupSelection(
            ticket,
            kind,
            path,
            identity,
            page_epoch,
            session_epoch,
            self._clock() + BACKUP_TTL_MS / 1000,
        )
        self._prune()
        self._selections[ticket] = selection
        while len(self._selections) > _MAX_TICKETS:
            self._selections.pop(next(iter(self._selections)))
        return self._selection_result(selection)

    def selection(
        self,
        ticket: str,
        kind: str,
        page_epoch: int,
        session_epoch: int,
        *,
        consume: bool,
    ) -> BackupSelection:
        self._prune()
        value = self._selections.get(ticket)
        if (
            value is None
            or value.kind != kind
            or value.page_epoch != page_epoch
            or value.session_epoch != session_epoch
        ):
            raise BackupRejected("SELECTION_EXPIRED")
        if consume:
            self._selections.pop(ticket, None)
        return value

    def restore_export_destination(self, value: BackupSelection) -> None:
        # 内容版本拒绝尚未写文件；保留原截止时间与文件身份，不重新授予路径权限。
        if value.kind == "DESTINATION" and value.expires_at > self._clock():
            self._selections[value.ticket] = value

    def install_preview(self, draft: BackupPreviewDraft) -> dict[str, object]:
        if draft.selection is None:
            raise BackupRejected("INVALID_ARGUMENT")
        selection = self.selection(
            draft.selection.ticket,
            "SOURCE",
            draft.selection.page_epoch,
            draft.selection.session_epoch,
            consume=False,
        )
        if file_identity(selection.path) != selection.identity:
            raise BackupRejected("SELECTION_EXPIRED")
        return self._install_preview(draft, selection.page_epoch, selection.session_epoch, selection)

    def install_received_preview(self, draft: BackupPreviewDraft, page_epoch: int, session_epoch: int) -> dict[str, object]:
        if draft.selection is not None or page_epoch <= 0 or session_epoch <= 0:
            raise BackupRejected("INVALID_ARGUMENT")
        return self._install_preview(draft, page_epoch, session_epoch, None)

    def _install_preview(self, draft: BackupPreviewDraft, page_epoch: int, session_epoch: int,
                         selection: BackupSelection | None) -> dict[str, object]:
        by_name = {
            str(row["platform"]): dict(row)
            for row in draft.current_records
        }
        conflicts = []
        for index, item in enumerate(draft.payload["passwords"]):
            current = by_name.get(item["platform"], {})
            identical = bool(current) and backup_password_content(current) == backup_password_content(item)
            conflicts.append(BackupConflict(
                hashlib.blake2s(f"{draft.retry_identity}:{index}:{item['platform']}".encode("utf-8"), digest_size=16).hexdigest(),
                item["platform"], current, item,
                decision="SKIP" if identical else "UNDECIDED", source_index=index,
                status="IDENTICAL" if identical else "CONFLICT" if current else "NEW",
                target_selected=bool(current),
            ))
        note_groups = backup_note_groups(list(draft.current_notes), draft.payload["notes"])
        identical_notes = backup_identical_note_targets(list(draft.current_notes), draft.payload["notes"])
        incoming_counts: dict[str, int] = {}
        for item in draft.payload["notes"]:
            key = similar_name_key(item["title"])
            incoming_counts[key] = incoming_counts.get(key, 0) + 1
        for index, item in enumerate(draft.payload["notes"]):
            key = similar_name_key(item["title"])
            candidates = note_groups[key]
            identical_id = identical_notes.get(index)
            selected = identical_id is not None or len(candidates) == 1
            target_index = next((position for position, row in enumerate(candidates) if row["id"] == identical_id), 0)
            status = "IDENTICAL" if identical_id is not None else "CONFLICT" if candidates or incoming_counts[key] > 1 else "NEW"
            conflicts.append(BackupConflict(
                hashlib.blake2s(f"{draft.retry_identity}:note:{index}".encode(), digest_size=16).hexdigest(),
                item["title"], candidates[target_index] if selected else {}, item,
                decision="SKIP" if identical_id is not None else "UNDECIDED",
                kind="NOTE", source_index=index, candidates=candidates, target_index=target_index,
                status=status, target_selected=selected,
            ))
        ticket = secrets.token_urlsafe(24)
        preview = BackupPreview(
            ticket,
            page_epoch,
            session_epoch,
            selection.ticket if selection else "",
            selection.path if selection else None,
            selection.identity if selection else None,
            draft.digest,
            draft.retry_identity,
            draft.payload,
            conflicts,
            note_groups,
            set(identical_notes.values()),
            received_snapshot=selection is None,
        )
        # 认证及快照构造完成时仍须持有原选文件资格，不能复活过期票据。
        if selection is not None:
            self.selection(selection.ticket, "SOURCE", page_epoch, session_epoch, consume=False)
        self._drop_previews(
            lambda value: value.page_epoch == page_epoch and value.session_epoch == session_epoch
        )
        self._retry_sources = {
            key: value for key, value in self._retry_sources.items()
            if selection is None or value != selection.ticket
        }
        self._previews[ticket] = preview
        self._clear_reads()
        return {
            "previewTicket": ticket,
            "backupLabel": selection.path.name if selection else "Device transfer",
            "passwordCount": len(draft.payload["passwords"]),
            "legacyRecoveryMissing": draft.payload["version"] == 1 and bool(draft.payload["passwords"]),
            "noteCount": len(draft.payload["notes"]),
            "conflictCount": sum(value.status == "CONFLICT" for value in conflicts),
            "passwordConflictCount": sum(value.kind == "PASSWORD" and value.status == "CONFLICT" for value in conflicts),
            "noteConflictCount": sum(value.kind == "NOTE" and value.status == "CONFLICT" for value in conflicts),
            "retryIdentity": draft.retry_identity,
            "expiresInMs": 0,
            "summary": self._import_summary(preview),
        }

    def begin_preview(self, source_ticket: str) -> None:
        self._drop_previews(
            lambda value: value.source_ticket == source_ticket
        )
        self._retry_sources = {
            key: value for key, value in self._retry_sources.items()
            if value != source_ticket
        }
        self._clear_reads()

    def list_conflicts(
        self,
        ticket: str,
        page_epoch: int,
        session_epoch: int,
        kind: str,
        cursor: str,
        limit: int,
        status_filter: str = "ALL",
        field_filter: str = "ALL",
    ) -> dict[str, object]:
        preview = self.preview(ticket, page_epoch, session_epoch)
        if (kind not in {"PASSWORD", "NOTE"} or status_filter not in {"ALL", "PENDING", "DIFFERENT", "SKIPPED"}
                or field_filter not in BUSINESS_FIELDS | {"ALL"}):
            raise BackupRejected("INVALID_ARGUMENT")
        self._clear_reads()
        if type(limit) is not int or not 1 <= limit <= 100:
            raise BackupRejected("INVALID_ARGUMENT")
        if cursor and (not cursor.isascii() or not cursor.isdigit()):
            raise BackupRejected("INVALID_ARGUMENT")
        offset = int(cursor or 0)
        conflicts = [value for value in preview.conflicts if value.kind == kind]
        matching_status = [value for value in conflicts if
                    (status_filter == "ALL" or status_filter == "PENDING" and value.status == "CONFLICT" and value.decision == "UNDECIDED"
                     or status_filter == "DIFFERENT" and value.status == "CONFLICT" and (value.current or value.candidates)
                     or status_filter == "SKIPPED" and value.decision == "SKIP")]
        selected = [value for value in matching_status
                    if (field_filter == "ALL" or value.current and value.target_selected and
                         self._value(value, value.current, field_filter) != self._value(value, value.incoming, field_filter))]
        offset = min(offset, max(0, (len(selected) - 1) // limit * limit))
        page = selected[offset:offset + limit]
        next_offset = offset + len(page)
        return {
            "kind": kind,
            "items": [self._summary(value, preview) for value in page],
            "total": len(selected),
            "unresolved": sum(
                value.status == "CONFLICT" and value.decision == "UNDECIDED" for value in conflicts
            ),
            "cursor": str(offset) if offset else "",
            "nextCursor": str(next_offset) if next_offset < len(selected) else "",
            "summary": self._import_summary(preview),
            "uncomparedCount": sum(len(value.candidates) > 1 and not value.target_selected for value in matching_status),
            "appliedIds": [],
            "remainingIds": [],
            "updatedItems": [],
        }

    def decide(
        self,
        ticket: str,
        page_epoch: int,
        session_epoch: int,
        conflict_id: str | None,
        decision: str,
        *,
        kind: str | None = None,
        conflict_ids: list[str] | None = None,
    ) -> dict[str, object]:
        preview = self.preview(ticket, page_epoch, session_epoch)
        self._clear_reads()
        if decision not in {"OVERWRITE", "SKIP", "KEEP", "SELECT_TARGET", "PREVIOUS_TARGET", "NEXT_TARGET"}:
            raise BackupRejected("INVALID_ARGUMENT")
        if conflict_id is None and decision not in {"OVERWRITE", "SKIP"} and not (
            kind == "NOTE" and decision == "KEEP"
        ):
            raise BackupRejected("INVALID_ARGUMENT")
        if conflict_id is None and kind not in {"PASSWORD", "NOTE"}:
            raise BackupRejected("INVALID_ARGUMENT")
        if conflict_id is None:
            if (type(conflict_ids) is not list or not 1 <= len(conflict_ids) <= 100
                    or any(type(value) is not str for value in conflict_ids)
                    or len(set(conflict_ids)) != len(conflict_ids)):
                raise BackupRejected("INVALID_ARGUMENT")
            wanted = set(conflict_ids)
            targets = [value for value in preview.conflicts if value.kind == kind and value.conflict_id in wanted]
            if len(targets) != len(wanted):
                raise BackupRejected("INVALID_ARGUMENT")
        else:
            targets = [value for value in preview.conflicts if value.conflict_id == conflict_id]
        if conflict_id is not None and not targets:
            raise BackupRejected("NOT_FOUND")
        if conflict_id is not None:
            kind = targets[0].kind
        if any(value.status != "CONFLICT" for value in targets):
            raise BackupRejected("INVALID_ARGUMENT")
        uses: dict[int, int] = {}
        applied_ids = []
        claimed = {value.current["id"]: value.conflict_id for value in preview.conflicts
                   if value.kind == "NOTE" and value.decision == "OVERWRITE"}
        for value in preview.conflicts:
            if value.kind == "NOTE" and value.status == "CONFLICT" and len(value.candidates) == 1:
                target_id = value.candidates[0]["id"]
                uses[target_id] = uses.get(target_id, 0) + 1
        for value in targets:
            if value.kind == "PASSWORD" and decision not in {"OVERWRITE", "SKIP"}:
                raise BackupRejected("INVALID_ARGUMENT")
            if value.kind == "NOTE":
                if decision in {"SELECT_TARGET", "PREVIOUS_TARGET", "NEXT_TARGET"}:
                    index = 0 if decision == "SELECT_TARGET" else value.target_index + (1 if decision == "NEXT_TARGET" else -1)
                    if not 0 <= index < len(value.candidates):
                        raise BackupRejected("INVALID_ARGUMENT")
                    if value.decision == "OVERWRITE":
                        claimed.pop(value.current["id"], None)
                    value.target_index = index
                    value.current = value.candidates[index]
                    value.target_selected = True
                    value.decision = "UNDECIDED"
                    applied_ids.append(value.conflict_id)
                    continue
                if decision == "OVERWRITE":
                    if conflict_id is None and (len(value.candidates) != 1 or uses.get(value.current.get("id"), 0) != 1
                                                or value.current.get("id") in preview.reserved_note_ids):
                        continue
                    if not value.target_selected or not value.current:
                        raise BackupRejected("INVALID_ARGUMENT")
                    if claimed.get(value.current["id"], value.conflict_id) != value.conflict_id or value.current["id"] in preview.reserved_note_ids:
                        if conflict_id is None:
                            continue
                        raise BackupRejected("REQUEST_BUSY")
                if value.decision == "OVERWRITE":
                    claimed.pop(value.current["id"], None)
                if decision == "OVERWRITE":
                    claimed[value.current["id"]] = value.conflict_id
            value.decision = decision
            applied_ids.append(value.conflict_id)
        result = self.list_conflicts(ticket, page_epoch, session_epoch, kind, "", 100)
        result["appliedIds"] = applied_ids
        result["remainingIds"] = [value.conflict_id for value in targets if value.conflict_id not in applied_ids]
        result["updatedItems"] = [self._summary(value, preview) for value in targets]
        return result

    def read_field(
        self,
        ticket: str,
        page_epoch: int,
        session_epoch: int,
        conflict_id: str,
        side: str,
        field: str,
        read_id: str,
        offset: int,
        *,
        secret: bool = True,
    ) -> dict[str, object]:
        preview = self.preview(ticket, page_epoch, session_epoch)
        allowed = SECRET_FIELDS if secret else TEXT_FIELDS
        if side not in {"CURRENT", "INCOMING"} or field not in allowed or type(offset) is not int or offset < 0:
            raise BackupRejected("INVALID_ARGUMENT")
        conflict = next(
            (value for value in preview.conflicts if value.conflict_id == conflict_id),
            None,
        )
        if conflict is None:
            raise BackupRejected("NOT_FOUND")
        if field not in (PASSWORD_FIELDS if conflict.kind == "PASSWORD" else NOTE_FIELDS):
            raise BackupRejected("INVALID_ARGUMENT")
        target_id = int(conflict.current.get("id", 0))
        detail = (ticket, conflict_id, target_id)
        binding = (ticket, conflict_id, field, target_id)
        now = self._clock()
        if not read_id:
            if side != "CURRENT" or secret and offset != 0:
                raise BackupRejected("INVALID_ARGUMENT")
            if self._active_read is not None:
                raise BackupRejected("REQUEST_BUSY")
            if self._detail != detail:
                self._clear_reads()
                self._detail = detail
            for previous_id, previous in tuple(self._reads.items()):
                if previous.binding[2] == field:
                    self.release_read(previous_id)
            read_id = secrets.token_urlsafe(24)
            self._reads[read_id] = _BackupRead(read_id, binding, now + BACKUP_FIELD_TTL_MS / 1000)
        current = self._reads.get(read_id)
        if current is None:
            raise BackupRejected("SECRET_LEASE_EXPIRED")
        if current.binding != binding or self._detail != detail:
            self.release_read(read_id)
            raise BackupRejected("INVALID_ARGUMENT")
        if side == "CURRENT":
            if self._active_read is not None:
                raise BackupRejected("REQUEST_BUSY")
        elif self._active_read != (read_id, offset):
            self.release_read(read_id)
            raise BackupRejected("INVALID_ARGUMENT")
        try:
            chunks, next_offset, done = self._pair_chunk(conflict, field, offset)
        except BackupRejected:
            self.release_read(read_id)
            raise
        self._active_read = (read_id, offset) if side == "CURRENT" else None
        result = {
            "readId": current.read_id,
            "text": chunks[0 if side == "CURRENT" else 1],
            "nextOffset": next_offset,
            "done": done,
            "expiresInMs": self._remaining_ms(current.expires_at),
        }
        return result

    @staticmethod
    def _value(value: BackupConflict, source: dict, field: str):
        if not source:
            return [] if field == "RECOVERY_CODES" else ""
        name = {"PLATFORM": "platform" if value.kind == "PASSWORD" else "title",
                "NOTES": "notes" if value.kind == "PASSWORD" else "content",
                "TOTP": "totp_secret", "FAVORITE": "is_favorite"}.get(field, field.lower())
        return source.get(name, [] if field == "RECOVERY_CODES" else "")

    @classmethod
    def _pair_chunk(cls, value: BackupConflict, field: str, offset: int) -> tuple[tuple[str, str], int, bool]:
        pair = [cls._value(value, source, field) for source in (value.current, value.incoming)]
        if field == "RECOVERY_CODES":
            length = max(map(len, pair))
            if offset > length:
                raise BackupRejected("INVALID_ARGUMENT")
            end = length
            while True:
                text = tuple(json.dumps(items[offset:end], ensure_ascii=False, separators=(",", ":")) for items in pair)
                if all(len(item) <= CHUNK_CHARACTERS and len(item.encode("utf-8")) <= CHUNK_UTF8_BYTES for item in text):
                    return text, end, end == length
                end -= 1
                if end <= offset:
                    raise BackupRejected("INVALID_ARGUMENT")
        text_pair = ["true" if item is True or field == "FAVORITE" and item == 1 else
                     "false" if item is False or field == "FAVORITE" and item == 0 else
                     "" if item is None else str(item) for item in pair]
        length = max(map(len, text_pair))
        if offset > length:
            raise BackupRejected("INVALID_ARGUMENT")
        end = min(length, offset + CHUNK_CHARACTERS)
        return tuple(item[offset:end] for item in text_pair), end, end == length

    def preview(self, ticket: str, page_epoch: int, session_epoch: int) -> BackupPreview:
        self._prune()
        value = self._previews.get(ticket)
        if (
            value is None
            or value.page_epoch != page_epoch
            or value.session_epoch != session_epoch
        ):
            raise BackupRejected("SECRET_LEASE_EXPIRED")
        return value

    def take_preview(self, ticket: str, page_epoch: int, session_epoch: int) -> BackupPreview:
        value = self.preview(ticket, page_epoch, session_epoch)
        self._previews.pop(ticket, None)
        self._clear_reads()
        return value

    def discard_preview(self, ticket: str) -> None:
        value = self._previews.pop(ticket, None)
        if value is not None:
            self._selections.pop(value.source_ticket, None)
            self._destroy_preview(value)
        self._retry_sources.pop(ticket, None)
        self._clear_reads()

    def discard_selection(self, ticket: str) -> None:
        self._selections.pop(ticket, None)
        self._drop_previews(lambda value: value.source_ticket == ticket)
        self._retry_sources = {
            key: value for key, value in self._retry_sources.items()
            if value != ticket
        }
        self._clear_reads()

    def finish_import(
        self,
        preview: BackupPreview,
        *,
        success: bool,
        retryable: bool,
    ) -> None:
        self._clear_reads()
        if success or not retryable:
            self._selections.pop(preview.source_ticket, None)
            self._retry_sources.pop(preview.ticket, None)
        elif not preview.received_snapshot:
            self._retry_sources[preview.ticket] = preview.source_ticket
        self._destroy_preview(preview)

    def close_capability(self, ticket: str, page_epoch: int, session_epoch: int) -> None:
        if ticket in self._reads:
            if self.read_is_current(ticket, page_epoch, session_epoch):
                self.release_read(ticket)
            return
        preview = self._previews.get(ticket)
        if preview is not None and (
            preview.page_epoch == page_epoch
            and preview.session_epoch == session_epoch
        ):
            self._previews.pop(ticket, None)
            self._selections.pop(preview.source_ticket, None)
            self._destroy_preview(preview)
            self._clear_reads()
            return
        selection = self._selections.get(ticket)
        if selection is not None and (
            selection.page_epoch == page_epoch
            and selection.session_epoch == session_epoch
        ):
            self.discard_selection(ticket)
        source_ticket = self._retry_sources.pop(ticket, None)
        if source_ticket is not None:
            self.discard_selection(source_ticket)

    def clear_page(self, page_epoch: int) -> None:
        self.clear_export_selection(page_epoch)
        self._selections = {
            key: value for key, value in self._selections.items()
            if value.page_epoch != page_epoch
        }
        self._drop_previews(lambda value: value.page_epoch == page_epoch)
        self._retry_sources = {
            key: value for key, value in self._retry_sources.items()
            if value in self._selections
        }
        self._clear_reads()

    def clear_session(self, session_epoch: int) -> None:
        for value in tuple(self._export_selections.values()):
            if value.session_epoch == session_epoch:
                self.clear_export_selection(value.page_epoch, session_epoch)
        self._selections = {
            key: value for key, value in self._selections.items()
            if value.session_epoch != session_epoch
        }
        self._drop_previews(lambda value: value.session_epoch == session_epoch)
        self._retry_sources = {
            key: value for key, value in self._retry_sources.items()
            if value in self._selections
        }
        self._clear_reads()

    def clear(self) -> None:
        for value in tuple(self._export_selections.values()):
            self.clear_export_selection(value.page_epoch)
        self._selections.clear()
        self._drop_previews(lambda _value: True)
        self._retry_sources.clear()
        self._clear_reads()

    def _clear_reads(self) -> None:
        self._reads.clear()
        self._active_read = None
        self._detail = None

    def release_read(self, read_id: str) -> None:
        self._reads.pop(read_id, None)
        if self._active_read is not None and self._active_read[0] == read_id:
            self._active_read = None

    def read_is_current(self, read_id: str, page_epoch: int, session_epoch: int) -> bool:
        self._prune()
        read = self._reads.get(read_id)
        preview = self._previews.get(read.binding[0]) if read else None
        return bool(preview and preview.page_epoch == page_epoch and preview.session_epoch == session_epoch
                    and self._detail == (read.binding[0], read.binding[1], read.binding[3]))

    def read_remaining_ms(self, read_id: str, page_epoch: int, session_epoch: int) -> int:
        if not self.read_is_current(read_id, page_epoch, session_epoch):
            return 0
        return self._remaining_ms(self._reads[read_id].expires_at)

    def _prune(self) -> None:
        now = self._clock()
        self._selections = {
            key: value for key, value in self._selections.items()
            if value.expires_at > now
        }
        self._retry_sources = {
            key: value for key, value in self._retry_sources.items()
            if value in self._selections
        }
        for read_id, read in tuple(self._reads.items()):
            if read.expires_at <= now or read.binding[0] not in self._previews:
                self.release_read(read_id)

    def _drop_previews(self, should_drop: Callable[[BackupPreview], bool]) -> None:
        kept: dict[str, BackupPreview] = {}
        for key, value in self._previews.items():
            if should_drop(value):
                self._destroy_preview(value)
            else:
                kept[key] = value
        self._previews = kept

    @staticmethod
    def _destroy_preview(preview: BackupPreview) -> None:
        preview.payload.clear()
        for conflict in preview.conflicts:
            conflict.current.clear()
            conflict.incoming.clear()
        preview.conflicts.clear()
        for rows in preview.note_groups.values():
            for row in rows:
                row.clear()
            rows.clear()
        preview.note_groups.clear()

    def _remaining_ms(self, expires_at: float) -> int:
        return max(0, min(BACKUP_TTL_MS, int((expires_at - self._clock()) * 1000)))

    @staticmethod
    def _import_summary(preview: BackupPreview) -> dict[str, int]:
        result = {"imported": 0, "overwritten": 0, "skipped": 0, "unresolved": 0, "recoveryCleared": 0}
        for value in preview.conflicts:
            if value.status == "IDENTICAL" or value.decision == "SKIP":
                result["skipped"] += 1
            elif value.status == "NEW" or value.decision == "KEEP":
                result["imported"] += 1
            elif value.decision == "OVERWRITE":
                result["overwritten"] += 1
                if value.kind == "PASSWORD" and value.current.get("recovery_codes") and not value.incoming.get("recovery_codes"):
                    result["recoveryCleared"] += 1
            else:
                result["unresolved"] += 1
        return result

    @classmethod
    def _summary(cls, value: BackupConflict, preview: BackupPreview) -> dict[str, object]:
        fields = PASSWORD_FIELDS if value.kind == "PASSWORD" else NOTE_FIELDS
        current_account = value.current.get("account" if value.kind == "PASSWORD" else "title", "")
        incoming_account = value.incoming["account" if value.kind == "PASSWORD" else "title"]
        current_name = cls._value(value, value.current, "PLATFORM")
        return {
            "conflictId": value.conflict_id,
            "kind": value.kind,
            "targetCount": int(bool(value.current)) if value.kind == "PASSWORD" else len(value.candidates),
            "targetIndex": value.target_index,
            "exactTitle": bool(value.current) and current_name == value.platform,
            "status": value.status,
            "decisionRequired": value.status == "CONFLICT",
            "targetSelected": value.target_selected,
            "targetProtected": value.current.get("id") in preview.reserved_note_ids if value.kind == "NOTE" else False,
            "businessDifferent": value.status == "CONFLICT" and (bool(value.current) if value.kind == "PASSWORD" else bool(value.candidates)),
            "differentFields": [name for name in fields if cls._value(value, value.current, name) != cls._value(value, value.incoming, name)]
                if value.current and value.target_selected else [],
            "platform": field_preview("PLATFORM", value.platform),
            "currentAccountDisplay": field_preview("ACCOUNT", current_account),
            "incomingAccountDisplay": field_preview("ACCOUNT", incoming_account),
            "currentLongFields": [name for name, text in (("PLATFORM", current_name), ("ACCOUNT", current_account)) if field_is_long(name, text)],
            "incomingLongFields": [name for name, text in (("PLATFORM", value.platform), ("ACCOUNT", incoming_account)) if field_is_long(name, text)],
            "hasCurrentPassword": bool(value.current.get("password")),
            "hasIncomingPassword": bool(value.incoming.get("password")),
            "hasCurrentNotes": bool(cls._value(value, value.current, "NOTES")),
            "hasIncomingNotes": bool(cls._value(value, value.incoming, "NOTES")),
            "hasCurrentTotp": bool(value.current.get("totp_secret")),
            "hasIncomingTotp": bool(value.incoming.get("totp_secret")),
            "hasCurrentRecovery": bool(value.current.get("recovery_codes", [])),
            "hasIncomingRecovery": bool(value.incoming.get("recovery_codes", [])),
            "decision": value.decision,
        }

    @staticmethod
    def _selection_result(value: BackupSelection | None) -> dict[str, object]:
        if value is None:
            return {
                "selected": False,
                "selectionTicket": "",
                "backupLabel": "",
                "expiresInMs": 0,
            }
        return {
            "selected": True,
            "selectionTicket": value.ticket,
            "backupLabel": value.path.name,
            "expiresInMs": BACKUP_TTL_MS,
        }

    @staticmethod
    def _normalize(value: Path, *, source: bool) -> Path:
        text = str(value)
        try:
            text_bytes = text.encode("utf-8")
            name_bytes = value.name.encode("utf-8")
        except UnicodeError as exc:
            raise BackupRejected("INVALID_ARGUMENT") from exc
        if (
            "\x00" in text
            or len(text) > 1024
            or len(text_bytes) > 4096
            or len(value.name) > 256
            or len(name_bytes) > 1024
            or not value.is_absolute()
            or not database_candidate_syntax_is_safe(value)
            or _has_reparse_component(value)
        ):
            raise BackupRejected("INVALID_ARGUMENT")
        try:
            resolved = value.resolve(strict=source)
            if _windows_drive_type(resolved) not in {2, 3}:
                raise BackupRejected("INVALID_ARGUMENT")
            return resolved
        except (OSError, RuntimeError) as exc:
            raise BackupRejected("NOT_FOUND" if source else "INVALID_ARGUMENT") from exc


def _has_reparse_component(path: Path) -> bool:
    current = path if path.exists() else path.parent
    while current != current.parent:
        if current.exists() and _is_windows_reparse_point(current):
            return True
        current = current.parent
    return current.exists() and _is_windows_reparse_point(current)


def file_identity(path: Path) -> tuple[int, int, int, int, int] | None:
    try:
        value = path.stat()
    except OSError:
        return None
    if not path.is_file():
        return None
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_size),
        int(value.st_ctime_ns),
        int(value.st_mtime_ns),
    )


def _read_limited(path: Path, limit: int) -> bytes:
    try:
        with path.open("rb") as handle:
            value = handle.read(limit + 1)
    except OSError as exc:
        raise BackupRejected("DATABASE_IO_FAILED") from exc
    if len(value) > limit:
        raise BackupRejected("BACKUP_LIMIT_EXCEEDED")
    return value


def read_backup_file(selection: BackupSelection) -> tuple[dict[str, object], str]:
    current_identity = file_identity(selection.path)
    if current_identity is not None and current_identity[2] > BACKUP_FILE_MAX_BYTES:
        raise BackupRejected("BACKUP_LIMIT_EXCEEDED")
    if current_identity != selection.identity:
        raise BackupRejected("SELECTION_EXPIRED")
    try:
        raw = _read_limited(selection.path, BACKUP_FILE_MAX_BYTES)
    except BackupRejected as exc:
        if str(exc) == "DATABASE_IO_FAILED":
            raise BackupRejected("SELECTION_EXPIRED") from exc
        raise
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BackupRejected("BACKUP_INVALID") from exc
    if not isinstance(value, dict):
        raise BackupRejected("BACKUP_INVALID")
    if file_identity(selection.path) != selection.identity:
        raise BackupRejected("SELECTION_EXPIRED")
    return value, hashlib.sha256(raw).hexdigest()


def source_matches(preview: BackupPreview) -> bool:
    if preview.received_snapshot:
        return preview.source_path is None and preview.source_identity is None and not preview.source_ticket
    if preview.source_path is None:
        return False
    current_identity = file_identity(preview.source_path)
    if (
        current_identity is None
        or current_identity[2] > BACKUP_FILE_MAX_BYTES
        or current_identity != preview.source_identity
    ):
        return False
    try:
        raw = _read_limited(preview.source_path, BACKUP_FILE_MAX_BYTES)
    except BackupRejected:
        return False
    return (
        hashlib.sha256(raw).hexdigest() == preview.source_digest
        and file_identity(preview.source_path) == preview.source_identity
    )


def encode_transfer_payload(payload: dict[str, object], guard: Callable[[], None]) -> bytes:
    """直传只封装业务内容；不生成文件、不更新本机备份记录。"""
    guard()
    validate_backup_payload(payload)
    encoded = bytearray()
    try:
        for part in json.JSONEncoder(ensure_ascii=False, separators=(",", ":")).iterencode(payload):
            guard()
            piece = part.encode("utf-8")
            if len(encoded) + len(piece) > BACKUP_FILE_MAX_BYTES:
                raise BackupError("transfer payload exceeds size limit", kind="size")
            encoded.extend(piece)
        guard()
        return bytes(encoded)
    finally:
        encoded.clear()


def parse_received_payload(encoded: bytes, expected_scope: str, expected_password_count: int,
                           expected_note_count: int) -> dict[str, object]:
    """只由已认证原生接收路径调用；范围及记录计数仍由本层严格复核。"""
    if type(encoded) is not bytes or not encoded:
        raise BackupError("transfer bytes are invalid", kind="payload")
    if len(encoded) > BACKUP_FILE_MAX_BYTES:
        raise BackupError("transfer payload exceeds size limit", kind="size")
    if (type(expected_scope) is not str or expected_scope not in {"ALL", "PASSWORDS", "NOTES"}
            or type(expected_password_count) is not int or type(expected_note_count) is not int
            or min(expected_password_count, expected_note_count) < 0
            or expected_password_count + expected_note_count > BACKUP_RECORD_MAX_ITEMS):
        raise BackupError("transfer metadata is invalid", kind="payload")

    def unique_fields(pairs):
        value = {}
        for name, item in pairs:
            if name in value:
                raise BackupError("duplicate transfer field", kind="payload")
            value[name] = item
        return value

    def reject_constant(_value):
        raise BackupError("non-finite transfer value", kind="payload")

    try:
        payload = json.loads(encoded.decode("utf-8"), object_pairs_hook=unique_fields, parse_constant=reject_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise BackupError("transfer JSON is invalid", kind="payload") from exc
    validate_backup_payload(payload)
    if (payload["scope"] != expected_scope or len(payload["passwords"]) != expected_password_count
            or len(payload["notes"]) != expected_note_count):
        raise BackupError("transfer metadata differs", kind="payload")
    return payload


def publish_envelope(
    selection: BackupSelection,
    envelope: dict[str, object],
    authorize: Callable[[], str | None],
) -> None:
    encoded = json.dumps(
        envelope,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > BACKUP_FILE_MAX_BYTES:
        raise BackupRejected("BACKUP_LIMIT_EXCEEDED")
    target = selection.path
    if not target.parent.is_dir():
        raise BackupRejected("DATABASE_IO_FAILED")
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".pdm-backup-tmp",
            dir=str(target.parent),
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            staged = _read_limited(temporary, len(encoded))
        except BackupRejected as exc:
            raise BackupRejected("DATABASE_IO_FAILED") from exc
        if staged != encoded:
            raise BackupRejected("DATABASE_IO_FAILED")
        if file_identity(target) != selection.identity:
            raise BackupRejected("SELECTION_EXPIRED")
        authorization_error = authorize()
        if authorization_error is not None:
            raise BackupRejected(authorization_error)
        if selection.identity is None:
            os.rename(temporary, target)
        else:
            os.replace(temporary, target)
        temporary = None
    except BackupRejected:
        raise
    except FileExistsError as exc:
        raise BackupRejected("SELECTION_EXPIRED") from exc
    except OSError as exc:
        raise BackupRejected("DATABASE_IO_FAILED") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


__all__ = [
    "BACKUP_FIELD_TTL_MS",
    "BACKUP_SUFFIX",
    "BACKUP_TTL_MS",
    "BackupController",
    "BackupFileSelector",
    "BackupPreview",
    "BackupPreviewDraft",
    "BackupRejected",
    "BackupSelection",
    "NativeBackupFileSelector",
    "NullBackupFileSelector",
    "publish_envelope",
    "read_backup_file",
    "source_matches",
]
