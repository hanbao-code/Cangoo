"""Explicitly isolated M4 production-slice candidate.

Nothing in this package is imported by the formal QWidget entry point.  The
WebEngine candidate imports it only when an isolation marker is supplied.
"""

from .isolation import (
    ISOLATION_MARKER_CONTENT,
    ISOLATION_MARKER_NAME,
    M4IsolationError,
    M4IsolationPaths,
)

__all__ = [
    "ISOLATION_MARKER_CONTENT",
    "ISOLATION_MARKER_NAME",
    "M4IsolationError",
    "M4IsolationPaths",
]
