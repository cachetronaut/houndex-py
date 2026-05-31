"""houndex-cli — operator + CI surface for the verification engine."""

from .commands import CommandDeps, CommandResult, ask, doctor, evaluate, ingest, init, verify
from .config import CONFIG_FILENAME, HoundexConfig, default_config, parse_config
from .embedder import SyntheticEmbedder
from .engine import (
    EvalFile,
    VerifyFile,
    build_answer_envelope,
    build_claim,
    default_verify_fixture,
    parse_claims,
    resolve_graph,
)

__all__ = [
    "CONFIG_FILENAME",
    "CommandDeps",
    "CommandResult",
    "EvalFile",
    "HoundexConfig",
    "SyntheticEmbedder",
    "VerifyFile",
    "ask",
    "build_answer_envelope",
    "build_claim",
    "default_config",
    "default_verify_fixture",
    "doctor",
    "evaluate",
    "ingest",
    "init",
    "parse_claims",
    "parse_config",
    "resolve_graph",
    "verify",
]
