"""为正式产品精确加载 Bridge v1.1（通信接口）合同。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from desktop.bridge.contract_catalog import ContractCatalog


_CONTRACT_SHA256 = (
    "341237f023a54466e40f88d801749ea7d55323424b6d662606ebb2279d36e53f"
)
_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "bridge_contract_v1.json"
)


def load_m4_contract() -> ContractCatalog:
    """Load one fixed developer-owned file and reject any byte drift."""

    data = _CONTRACT_PATH.read_bytes()
    if hashlib.sha256(data).hexdigest() != _CONTRACT_SHA256:
        raise RuntimeError("frozen Bridge v1.1 contract hash mismatch")
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("frozen Bridge v1.1 contract is not an object")
    return ContractCatalog.from_mapping(value)


__all__ = ["load_m4_contract"]
