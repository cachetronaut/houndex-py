#!/usr/bin/env python3
"""Clean-room guard.

Fails if any disallowed token appears in a git-tracked file. This keeps the
public framework free of names and terminology carried over from the
applications that use it. Run via `uv run python scripts/cleanroom_guard.py`
and in CI.

To intentionally allow a term, remove it from BANNED below with a comment
explaining why, or add a specific path to ALLOWED_PATHS.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Case-insensitive substrings that must never appear in tracked source.
BANNED = [
    "aquir",
    "competitor",
    "competitive",
    "positioning",
    "talkingpoint",
    "buyersignal",
    "crowdstrike",
    "splunk",
    "market_position",
    "customer_segment",
]

# Files exempt from the scan (this guard declares the banned list itself).
ALLOWED_PATHS = {"scripts/cleanroom_guard.py"}

# Extensions we treat as text and therefore scan.
TEXT_EXT = {
    ".py",
    ".pyi",
    ".toml",
    ".cfg",
    ".ini",
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".sql",
    ".sh",
    ".cff",
}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def main() -> int:
    lowered = [term.lower() for term in BANNED]
    violations: list[tuple[str, int, str, str]] = []

    for file in tracked_files():
        if file in ALLOWED_PATHS:
            continue
        if Path(file).suffix not in TEXT_EXT:
            continue
        try:
            contents = Path(file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in enumerate(contents.splitlines(), start=1):
            low = line.lower()
            for term in lowered:
                if term in low:
                    violations.append((file, line_no, term, line.strip()))

    if violations:
        print("Clean-room guard FAILED — disallowed tokens found:\n", file=sys.stderr)
        for file, line_no, term, text in violations:
            print(f"  {file}:{line_no}  [{term}]  {text}", file=sys.stderr)
        print(
            f"\n{len(violations)} violation(s). See scripts/cleanroom_guard.py.",
            file=sys.stderr,
        )
        return 1

    print(f"Clean-room guard passed ({len(BANNED)} terms checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
