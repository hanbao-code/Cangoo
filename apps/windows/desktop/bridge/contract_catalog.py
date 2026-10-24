"""当前 Bridge v1.1（通信接口）机器合同的不可变运行视图。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import re
from typing import Any, Mapping

from .command_ids import CommandId


SCALAR_ARGUMENT_KINDS = {"boolean", "integer", "string", "enum"}
SECRET_LEASE_TTL_KEYS = {
    CommandId.C12: "editor_secret_lease_ttl_ms",
    CommandId.C13: "record_reveal_delivery_ttl_ms",
    CommandId.C77: "record_reveal_delivery_ttl_ms",
    CommandId.C33: "generated_secret_lease_ttl_ms",
}


class ContractViolation(RuntimeError):
    """The trusted contract itself is malformed or unsupported."""


class ValueRejected(ValueError):
    """A request or result value does not match its frozen type."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


@dataclass(frozen=True, slots=True)
class ArgumentSpec:
    name: str
    type_name: str


@dataclass(frozen=True, slots=True)
class LifecycleSpec:
    name: str
    max_in_flight: int
    duplicate: str
    cancel: str
    late_result: str
    invalidate_on: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommandSpec:
    command_id: CommandId
    method: str
    surface: str
    completion_signal: str | None
    authority: str
    auth: str
    arguments: tuple[ArgumentSpec, ...]
    result_type: str
    writes: str
    input_sensitivity: str
    output_sensitivity: str
    lifecycle: str
    errors: frozenset[str]


class ContractCatalog:
    """Validated catalog used by the request boundary.

    The caller provides the already loaded JSON object.  Production code does
    not discover a documentation path, and the isolated M3.3 verifier is the
    only current caller.
    """

    def __init__(self, contract: Mapping[str, Any]) -> None:
        raw = deepcopy(dict(contract))
        _require(raw.get("contract_version") == "1.1.0", "contract version")
        wire = raw.get("wire")
        types = raw.get("types")
        commands = raw.get("commands")
        lifecycles = raw.get("lifecycle_profiles")
        resource_limits = raw.get("resource_limits")
        _require(isinstance(wire, dict), "wire policy")
        _require(isinstance(types, dict) and types, "type catalog")
        _require(isinstance(commands, list) and commands, "command catalog")
        _require(isinstance(lifecycles, dict) and lifecycles, "lifecycles")
        _require(
            isinstance(resource_limits, dict),
            "resource limit catalog",
        )

        self._wire = wire
        self._resource_limits = resource_limits
        self._types: dict[str, dict[str, Any]] = {}
        for name, definition in types.items():
            _require(
                isinstance(name, str) and isinstance(definition, dict),
                "type declaration",
            )
            self._types[name] = definition

        self._lifecycles: dict[str, LifecycleSpec] = {}
        for name, definition in lifecycles.items():
            _require(isinstance(definition, dict), "lifecycle declaration")
            self._lifecycles[name] = LifecycleSpec(
                name=name,
                max_in_flight=int(definition["max_in_flight"]),
                duplicate=str(definition["duplicate"]),
                cancel=str(definition["cancel"]),
                late_result=str(definition["late_result"]),
                invalidate_on=tuple(definition["invalidate_on"]),
            )

        self._commands: dict[CommandId, CommandSpec] = {}
        for definition in commands:
            _require(isinstance(definition, dict), "command declaration")
            command_id = CommandId(definition["id"])
            arguments = tuple(
                ArgumentSpec(name=item[0], type_name=item[1])
                for item in definition["arguments"]
            )
            for argument in arguments:
                _require(
                    self._types[argument.type_name]["kind"] in SCALAR_ARGUMENT_KINDS
                    or command_id is CommandId.C56 and argument.name == "conflictIds"
                    and argument.type_name == "BackupSelectedIds",
                    f"{command_id.value} has a non-scalar wire argument",
                )
            spec = CommandSpec(
                command_id=command_id,
                method=str(definition["method"]),
                surface=str(definition["surface"]),
                completion_signal=definition.get("completion_signal"),
                authority=str(definition["authority"]),
                auth=str(definition["auth"]),
                arguments=arguments,
                result_type=str(definition["result"]),
                writes=str(definition["writes"]),
                input_sensitivity=str(definition["input_sensitivity"]),
                output_sensitivity=str(definition["output_sensitivity"]),
                lifecycle=str(definition["lifecycle"]),
                errors=frozenset(definition["errors"]),
            )
            _require(
                spec.command_id not in self._commands,
                "duplicate command identifier",
            )
            _require(spec.result_type in self._types, "unknown result type")
            _require(spec.lifecycle in self._lifecycles, "unknown lifecycle")
            self._commands[spec.command_id] = spec

        _require(
            set(self._commands) == set(CommandId),
            "generated CommandId allowlist differs from the contract",
        )
        for key in SECRET_LEASE_TTL_KEYS.values():
            value = self._resource_limits.get(key)
            _require(
                type(value) is int and 0 < value <= 600_000,
                f"invalid secret lease resource limit: {key}",
            )

    @classmethod
    def from_mapping(
        cls,
        contract: Mapping[str, Any],
    ) -> "ContractCatalog":
        return cls(contract)

    @property
    def max_request_utf8_bytes(self) -> int:
        return int(self._wire["max_request_utf8_bytes"])

    @property
    def max_in_flight_per_page(self) -> int:
        return int(self._wire["max_in_flight_per_page"])

    @property
    def completed_cache_items(self) -> int:
        return int(self._wire["completed_request_cache_items"])

    @property
    def completed_cache_seconds(self) -> int:
        return int(self._wire["completed_request_cache_seconds"])

    @property
    def retired_page_instance_cache_items(self) -> int:
        return int(self._wire["retired_page_instance_cache_items"])

    def secret_lease_ttl_ms(self, command_id: CommandId) -> int:
        """Return the frozen pre-delivery or expiring-lease TTL."""

        try:
            key = SECRET_LEASE_TTL_KEYS[command_id]
        except KeyError as exc:
            raise ContractViolation(
                f"{command_id.value} does not produce a secret lease"
            ) from exc
        return int(self._resource_limits[key])

    def command(self, command_id: CommandId) -> CommandSpec:
        return self._commands[command_id]

    def lifecycle(self, name: str) -> LifecycleSpec:
        return self._lifecycles[name]

    def type_definition(self, type_name: str) -> Mapping[str, Any]:
        return self._types[type_name]

    def validate_value(self, type_name: str, value: object) -> None:
        """Validate one exact bounded value without coercion."""

        definition = self._types[type_name]
        kind = definition["kind"]
        if kind == "boolean":
            if type(value) is not bool:
                raise ValueRejected(type_name)
            return
        if kind == "integer":
            if type(value) is not int:
                raise ValueRejected(type_name)
            if not (
                int(definition["minimum"])
                <= value
                <= int(definition["maximum"])
            ):
                raise ValueRejected(type_name)
            return
        if kind == "string":
            if type(value) is not str:
                raise ValueRejected(type_name)
            if not (
                int(definition["min_chars"])
                <= len(value)
                <= int(definition["max_chars"])
            ):
                raise ValueRejected(type_name)
            try:
                encoded = value.encode("utf-8", errors="strict")
            except UnicodeError as exc:
                raise ValueRejected(type_name) from exc
            if len(encoded) > int(definition["max_utf8_bytes"]):
                raise ValueRejected(type_name)
            if definition.get("reject_nul") and "\x00" in value:
                raise ValueRejected(type_name)
            pattern = definition.get("pattern")
            if pattern is not None and re.fullmatch(pattern, value) is None:
                raise ValueRejected(type_name)
            return
        if kind == "enum":
            if type(value) is not str or value not in definition["values"]:
                raise ValueRejected(type_name)
            return
        if kind == "array":
            if type(value) is not list:
                raise ValueRejected(type_name)
            if len(value) > int(definition["max_items"]):
                raise ValueRejected(type_name)
            item_type = definition["items"]
            for item in value:
                self.validate_value(item_type, item)
            if type_name in {"BackupSelectedIds", "BackupIdList"}:
                if len(value) != len(set(value)) or type_name == "BackupSelectedIds" and not value:
                    raise ValueRejected(type_name)
            return
        if kind == "object":
            if type(value) is not dict:
                raise ValueRejected(type_name)
            fields = definition["fields"]
            allowed = {field["name"] for field in fields}
            required = {
                field["name"]
                for field in fields
                if field.get("required") is True
            }
            keys = set(value)
            if not required <= keys or not keys <= allowed:
                raise ValueRejected(type_name)
            for field in fields:
                if field["name"] in value:
                    self.validate_value(
                        field["type"],
                        value[field["name"]],
                    )
            return
        raise ContractViolation(f"unsupported type kind: {kind}")

    def wire_size(self, arguments: tuple[object, ...]) -> int:
        """Return the deterministic UTF-8 size of positional scalar values."""

        rendered = json.dumps(
            arguments,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        return len(rendered.encode("utf-8"))

    def type_graph(self, root_type: str) -> set[str]:
        seen: set[str] = set()
        pending = [root_type]
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            definition = self._types[current]
            if definition["kind"] == "array":
                pending.append(definition["items"])
            elif definition["kind"] == "object":
                pending.extend(
                    field["type"] for field in definition["fields"]
                )
        return seen

    def type_is_sensitive(self, root_type: str) -> bool:
        return any(
            self._types[type_name].get("sensitive") is True
            or self._types[type_name].get("secret_result") is True
            for type_name in self.type_graph(root_type)
        )

    def command_has_sensitive_input(self, spec: CommandSpec) -> bool:
        return any(
            self.type_is_sensitive(argument.type_name)
            for argument in spec.arguments
        )

    def command_has_sensitive_result(self, spec: CommandSpec) -> bool:
        return self.type_is_sensitive(spec.result_type)

    def command_can_replay(self, spec: CommandSpec) -> bool:
        lifecycle = self.lifecycle(spec.lifecycle)
        return (
            "replay" in lifecycle.duplicate
            and "never_cache" not in lifecycle.duplicate
            and not self.command_has_sensitive_input(spec)
            and not self.command_has_sensitive_result(spec)
        )
