"""Isolated M3 typed Bridge and native secret-lifecycle boundary.

No adapter in this package touches core, a database, configuration, native
capabilities, or user state.  The fake used by verification lives under
``tools/`` and cannot be registered as a production adapter.
"""

from .command_ids import CommandId
from .contract_catalog import ContractCatalog
from .native_quickbar import NativeQuickbarPort
from .protocol import (
    AdapterCompletion,
    AdapterRequest,
    BridgeAdapter,
    CompletionEnvelope,
    NullSecretLifecycleSink,
    NullSecurityBoundarySink,
    SecretLifecycleSink,
    SecurityBoundaryOutcome,
    SecurityBoundarySink,
)
from .secret_leases import (
    SecretLease,
    SecretLeaseKind,
    SecretLeaseRegistry,
    SecretLeaseRejected,
    SecretLeaseRule,
)
from .web_bridge import PdmBridgeV1

__all__ = [
    "AdapterCompletion",
    "AdapterRequest",
    "BridgeAdapter",
    "CommandId",
    "CompletionEnvelope",
    "ContractCatalog",
    "NativeQuickbarPort",
    "NullSecretLifecycleSink",
    "NullSecurityBoundarySink",
    "PdmBridgeV1",
    "SecretLease",
    "SecretLeaseKind",
    "SecretLeaseRegistry",
    "SecretLeaseRejected",
    "SecretLeaseRule",
    "SecretLifecycleSink",
    "SecurityBoundaryOutcome",
    "SecurityBoundarySink",
]
