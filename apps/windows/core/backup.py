"""Portable encrypted backup envelope for password-manager exports.

The database service deliberately returns a plain Python structure so it can be
used by the UI and tests.  This module is the file boundary: it derives an
independent backup key and serialises that structure into an authenticated,
portable JSON envelope.  No plaintext records are written to the backup file.
"""
from __future__ import annotations

import base64
import datetime
import json
import re
from typing import Any

from core.recovery_codes import RecoveryCodeError, validate_codes

from core.crypto import (
    ARGON2_HASH_LEN,
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
    CryptoHelper,
)


BACKUP_TYPE = "password_manager_encrypted_backup"


def similar_name_key(value: str) -> str:
    """沿既定名称规则移除Unicode空白并折叠大小写。"""
    return "".join(character for character in value if not character.isspace()).casefold()


def backup_note_groups(rows: list[dict], incoming: list[dict]) -> dict[str, list[dict]]:
    """只保留本次来源标题相关的目标，按稳定ID排列供预览和事务复核。"""
    groups = {similar_name_key(item["title"]): [] for item in incoming}
    for row in rows:
        key = similar_name_key(row["title"])
        if key in groups:
            groups[key].append(row)
    for values in groups.values():
        values.sort(key=lambda value: value["id"])
    return groups


def backup_password_content(record: dict) -> tuple:
    """已校验密码的业务值；版本、时间和评分仍由完整快照独立复核。"""
    return (
        record["platform"], record["account"], record["password"], record["notes"],
        record["totp_secret"],
        tuple((code["value"], code["used"]) for code in record.get("recovery_codes", [])),
        record["is_favorite"],
    )


def backup_note_content(record: dict) -> tuple:
    """记事按原始标题、正文和收藏比较，不按近名或排列位置判相同。"""
    return record["title"], record["content"], record["is_favorite"]


def backup_identical_note_targets(rows: list[dict], incoming: list[dict]) -> dict[int, int]:
    """只在提交前目标集合中匹配，每组相同内容保留最小稳定ID。"""
    contents = [backup_note_content(item) for item in incoming]
    wanted = set(contents)
    matching = {}
    for row in rows:
        content = backup_note_content(row)
        if content in wanted:
            matching[content] = min(matching.get(content, row["id"]), row["id"])
    return {index: matching[content] for index, content in enumerate(contents) if content in matching}


BACKUP_VERSION = 1
BACKUP_V2_VERSION = 2
BACKUP_PAYLOAD_TYPE = "password_manager_backup_payload"
BACKUP_PAYLOAD_VERSION = 2
BACKUP_FILE_MAX_BYTES = 64 * 1024 * 1024
BACKUP_RECORD_MAX_ITEMS = 100_000

_ENVELOPE_FIELDS = {"type", "version", "kdf", "payload"}
_KDF_FIELDS = {
    "name",
    "salt",
    "memory_cost",
    "time_cost",
    "parallelism",
    "hash_len",
}
_PAYLOAD_FIELDS = {
    "type",
    "version",
    "export_time",
    "scope",
    "passwords",
    "notes",
}
_PASSWORD_FIELDS = {
    "platform",
    "account",
    "password",
    "notes",
    "totp_secret",
    "strength",
    "password_changed_at",
    "updated_at",
    "is_favorite",
}
_NOTE_FIELDS = {
    "title",
    "content",
    "created_at",
    "updated_at",
    "sort_order",
    "is_favorite",
}
_TOTP_PATTERN = re.compile(r"^[A-Za-z2-7= \-]*$")


class BackupError(ValueError):
    """A backup file is malformed or cannot be authenticated.

    ``kind`` is intentionally coarse.  It lets the UI distinguish a visibly
    malformed envelope from an authentication failure without exposing crypto
    implementation details (or pretending it can distinguish a wrong password
    from authenticated data corruption).
    """

    def __init__(self, message: str, *, kind: str = "format") -> None:
        super().__init__(message)
        self.kind = kind


def encrypt_backup(data: dict[str, Any], password: str) -> dict[str, Any]:
    """Return a JSON-safe encrypted backup envelope for *data*.

    ``password`` is intentionally independent from the database password.  The
    random salt is metadata, while the complete payload is protected by
    AES-256-GCM authentication.
    """
    if not isinstance(data, dict):
        raise BackupError("backup payload must be an object", kind="payload")
    if not password:
        raise BackupError("backup password is required", kind="password")
    salt = CryptoHelper.generate_salt()
    key = CryptoHelper.derive_key(password, salt)
    plaintext = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return {
        "type": BACKUP_TYPE,
        "version": BACKUP_VERSION,
        "kdf": {
            "name": "argon2id",
            "salt": base64.b64encode(salt).decode("ascii"),
        },
        "payload": CryptoHelper.encrypt_data(plaintext, key),
    }


def decrypt_backup(envelope: dict[str, Any], password: str) -> dict[str, Any]:
    """Authenticate and return the original export structure.

    All parsing/authentication failures are deliberately normalised to
    ``BackupError`` so callers do not leak cryptographic implementation detail
    into the UI.
    """
    if not password:
        raise BackupError("backup password is required", kind="password")
    try:
        if not isinstance(envelope, dict):
            raise BackupError("backup envelope must be an object")
        if envelope.get("type") != BACKUP_TYPE or envelope.get("version") != BACKUP_VERSION:
            raise BackupError("unsupported backup format")
        kdf = envelope["kdf"]
        if not isinstance(kdf, dict):
            raise BackupError("invalid backup key derivation")
        if kdf.get("name") != "argon2id":
            raise BackupError("unsupported backup key derivation")
        salt = base64.b64decode(kdf["salt"], validate=True)
        if len(salt) != 16:
            raise BackupError("invalid backup salt")
        key = CryptoHelper.derive_key(password, salt)
        try:
            plaintext = CryptoHelper.decrypt_data(envelope["payload"], key)
        except Exception as exc:
            raise BackupError("backup authentication failed", kind="auth") from exc
        try:
            data = json.loads(plaintext)
        except Exception as exc:
            raise BackupError("backup payload is not valid JSON", kind="payload") from exc
    except BackupError:
        raise
    except Exception as exc:
        raise BackupError("backup envelope is malformed") from exc
    if not isinstance(data, dict):
        raise BackupError("backup payload must be an object", kind="payload")
    return data


def encrypt_backup_v2(
    payload: dict[str, Any],
    password: str,
) -> dict[str, Any]:
    """校验并加密受支持的版本化备份载荷。"""

    _validate_password(password)
    _validate_payload(payload)
    plaintext = _payload_json(payload)
    salt = CryptoHelper.generate_salt()
    key = CryptoHelper.derive_key(password, salt)
    envelope = {
        "type": BACKUP_TYPE,
        "version": BACKUP_V2_VERSION,
        "kdf": {
            "name": "argon2id",
            "salt": base64.b64encode(salt).decode("ascii"),
            "memory_cost": ARGON2_MEMORY_COST,
            "time_cost": ARGON2_TIME_COST,
            "parallelism": ARGON2_PARALLELISM,
            "hash_len": ARGON2_HASH_LEN,
        },
        "payload": CryptoHelper.encrypt_data(plaintext, key),
    }
    if len(_json_bytes(envelope)) > BACKUP_FILE_MAX_BYTES:
        raise BackupError("backup file exceeds size limit", kind="size")
    return envelope


def decrypt_backup_v2(
    envelope: dict[str, Any],
    password: str,
) -> dict[str, Any]:
    """认证严格的 v2 外层并返回已校验载荷。"""

    _validate_password(password)
    if not isinstance(envelope, dict) or set(envelope) != _ENVELOPE_FIELDS:
        raise BackupError("backup envelope fields are invalid")
    if (
        envelope.get("type") != BACKUP_TYPE
        or type(envelope.get("version")) is not int
        or envelope.get("version") != BACKUP_V2_VERSION
    ):
        raise BackupError("unsupported backup format")
    if len(_json_bytes(envelope)) > BACKUP_FILE_MAX_BYTES:
        raise BackupError("backup file exceeds size limit", kind="size")
    kdf = envelope.get("kdf")
    if not isinstance(kdf, dict) or set(kdf) != _KDF_FIELDS:
        raise BackupError("backup key derivation fields are invalid")
    expected_kdf = {
        "name": "argon2id",
        "memory_cost": ARGON2_MEMORY_COST,
        "time_cost": ARGON2_TIME_COST,
        "parallelism": ARGON2_PARALLELISM,
        "hash_len": ARGON2_HASH_LEN,
    }
    if (
        not isinstance(kdf.get("name"), str)
        or any(
            type(kdf.get(name)) is not int or kdf.get(name) != value
            for name, value in expected_kdf.items()
            if name != "name"
        )
        or kdf.get("name") != expected_kdf["name"]
    ):
        raise BackupError("unsupported backup key derivation")
    salt_value = kdf.get("salt")
    encrypted = envelope.get("payload")
    if not isinstance(salt_value, str) or not isinstance(encrypted, str):
        raise BackupError("backup envelope values are invalid")
    try:
        salt = base64.b64decode(salt_value, validate=True)
        encrypted_bytes = base64.b64decode(encrypted, validate=True)
    except Exception as exc:
        raise BackupError("backup envelope encoding is invalid") from exc
    if len(salt) != 16 or len(encrypted_bytes) < 28:
        raise BackupError("backup envelope encoding is invalid")
    key = CryptoHelper.derive_key(password, salt)
    try:
        plaintext = CryptoHelper.decrypt_data(encrypted, key)
    except Exception as exc:
        raise BackupError("backup authentication failed", kind="auth") from exc
    if len(plaintext.encode("utf-8")) > BACKUP_FILE_MAX_BYTES:
        raise BackupError("backup payload exceeds size limit", kind="size")
    try:
        payload = json.loads(plaintext)
    except Exception as exc:
        raise BackupError("backup payload is not valid JSON", kind="payload") from exc
    _validate_payload(payload)
    return payload


def validate_backup_payload(payload: object) -> None:
    """供数据库导入导出边界复用的 core 校验入口。"""

    _validate_payload(payload)


def _validate_payload(payload: object) -> None:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_FIELDS:
        raise BackupError("backup payload fields are invalid", kind="payload")
    if (
        payload.get("type") != BACKUP_PAYLOAD_TYPE
        or type(payload.get("version")) is not int
        or payload.get("version") not in {1, BACKUP_PAYLOAD_VERSION}
    ):
        raise BackupError("unsupported backup payload", kind="payload")
    _validate_timestamp(payload.get("export_time"), "export_time")
    scope = payload.get("scope")
    if not isinstance(scope, str) or scope not in {"ALL", "PASSWORDS", "NOTES"}:
        raise BackupError("backup scope is invalid", kind="payload")
    passwords = payload.get("passwords")
    notes = payload.get("notes")
    if not isinstance(passwords, list) or not isinstance(notes, list):
        raise BackupError("backup record collections are invalid", kind="payload")
    if len(passwords) + len(notes) > BACKUP_RECORD_MAX_ITEMS:
        raise BackupError("backup record count exceeds limit", kind="size")
    if scope == "PASSWORDS" and notes:
        raise BackupError("password-only backup contains notes", kind="payload")
    if scope == "NOTES" and passwords:
        raise BackupError("note-only backup contains passwords", kind="payload")

    seen_platforms: set[str] = set()
    for item in passwords:
        _validate_password_record(item, version=payload["version"])
        platform = item["platform"]
        if platform in seen_platforms:
            raise BackupError("backup contains duplicate record names", kind="payload")
        seen_platforms.add(platform)
    for item in notes:
        _validate_note_record(item)
    if len(_payload_json(payload).encode("utf-8")) > BACKUP_FILE_MAX_BYTES:
        raise BackupError("backup payload exceeds size limit", kind="size")


def _validate_password_record(value: object, *, version: int) -> None:
    fields = _PASSWORD_FIELDS | ({"recovery_codes"} if version == 2 else set())
    if not isinstance(value, dict) or set(value) != fields:
        raise BackupError("backup password record fields are invalid", kind="payload")
    platform = _validate_text(value.get("platform"), "platform", required=True)
    if not platform.strip():
        raise BackupError("backup record name is all whitespace", kind="payload")
    for field in ("account", "password", "notes"):
        _validate_text(value.get(field), field)
    totp_secret = _validate_text(
        value.get("totp_secret"),
        "totp_secret",
        max_chars=256,
        max_bytes=512,
    )
    if not _TOTP_PATTERN.fullmatch(totp_secret):
        raise BackupError("backup TOTP secret is invalid", kind="payload")
    if version == 2:
        try:
            validate_codes(value["recovery_codes"])
        except RecoveryCodeError as exc:
            raise BackupError("backup recovery codes are invalid", kind="payload") from exc
    strength = value.get("strength")
    if strength is not None and (
        not isinstance(strength, str) or strength not in {"weak", "fair", "strong"}
    ):
        raise BackupError("backup strength is invalid", kind="payload")
    if value.get("password_changed_at") is not None:
        _validate_timestamp(value.get("password_changed_at"), "password_changed_at")
    _validate_timestamp(value.get("updated_at"), "updated_at")
    if type(value.get("is_favorite")) is not bool:
        raise BackupError("backup favorite value is invalid", kind="payload")


def _validate_note_record(value: object) -> None:
    if not isinstance(value, dict) or set(value) != _NOTE_FIELDS:
        raise BackupError("backup note fields are invalid", kind="payload")
    title = _validate_text(value.get("title"), "title", required=True)
    if not title.strip():
        raise BackupError("backup note title is all whitespace", kind="payload")
    _validate_text(value.get("content"), "content")
    _validate_timestamp(value.get("created_at"), "created_at")
    _validate_timestamp(value.get("updated_at"), "updated_at")
    sort_order = value.get("sort_order")
    if type(sort_order) is not int or not -(2**31) <= sort_order < 2**31:
        raise BackupError("backup note order is invalid", kind="payload")
    if type(value.get("is_favorite")) is not bool:
        raise BackupError("backup favorite value is invalid", kind="payload")


def _validate_password(password: object) -> None:
    _validate_text(
        password,
        "backup password",
        required=True,
        max_chars=1024,
        max_bytes=4096,
        kind="password",
    )


def _validate_text(
    value: object,
    field: str,
    *,
    required: bool = False,
    max_chars: int = BACKUP_FILE_MAX_BYTES,
    max_bytes: int = BACKUP_FILE_MAX_BYTES,
    kind: str = "payload",
) -> str:
    if not isinstance(value, str) or (required and not value):
        raise BackupError(f"{field} is invalid", kind=kind)
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as exc:
        raise BackupError(f"{field} is invalid Unicode", kind=kind) from exc
    if "\x00" in value or len(value) > max_chars or len(encoded) > max_bytes:
        raise BackupError(f"{field} exceeds its limit", kind=kind)
    return value


def _validate_timestamp(value: object, field: str) -> None:
    text = _validate_text(value, field, required=True, max_chars=64, max_bytes=64)
    try:
        datetime.datetime.fromisoformat(text)
    except ValueError as exc:
        raise BackupError(f"{field} is not an ISO timestamp", kind="payload") from exc


def _payload_json(payload: object) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise BackupError("backup payload is not JSON-safe", kind="payload") from exc


def _json_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise BackupError("backup envelope is not JSON-safe") from exc
