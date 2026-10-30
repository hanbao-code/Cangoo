"""类型化网页桥接、原生快速栏端口与秘密生命周期边界。"""

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
