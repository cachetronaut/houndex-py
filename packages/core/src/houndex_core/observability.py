"""Minimal, dependency-free observability seam.

Core emits structured events through a ``TraceSink`` rather than importing a
tracing vendor. The default sink is a no-op, so the framework adds zero overhead
until an application plugs in its own sink.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TraceEvent:
    # Dotted event name, e.g. "ingest.chunk" or "claim.upsert".
    name: str
    # Arbitrary structured attributes; keep values JSON-serializable.
    attributes: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class TraceSink(Protocol):
    def emit(self, event: TraceEvent) -> None: ...


class NoopTraceSink:
    def emit(self, event: TraceEvent) -> None:
        return None


_active_sink: TraceSink = NoopTraceSink()


def set_trace_sink(sink: TraceSink) -> TraceSink:
    """Install the process-wide trace sink. Returns the previously active sink."""
    global _active_sink
    previous = _active_sink
    _active_sink = sink
    return previous


def emit_trace(event: TraceEvent) -> None:
    _active_sink.emit(event)
