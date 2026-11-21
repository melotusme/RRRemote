"""Shared helpers for idempotent, verified RRRemote Flutter UI patches."""

from __future__ import annotations

import re
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def replace_exact(
    content: str, old: str, new: str, label: str, required: bool = True
) -> str:
    if not new:
        raise ValueError(
            f"replace_exact requires non-empty replacement for idempotency: {label}"
        )
    if new in content:
        print(f"[rrremote-ui] already applied: {label}")
        return content
    if old not in content:
        msg = f"[rrremote-ui] pattern NOT matched: {label}"
        if required:
            raise RuntimeError(msg)
        print(f"WARNING: {msg}")
        return content
    print(f"[rrremote-ui] applied: {label}")
    return content.replace(old, new, 1)


def ensure_import(content: str, import_line: str) -> str:
    if import_line in content:
        return content
    m = re.search(
        r"^import\s+['\"][^'\"]+['\"][^;]*;\s*$", content, flags=re.MULTILINE
    )
    if not m:
        return import_line + "\n" + content
    idx = m.end()
    return content[:idx] + "\n" + import_line + content[idx:]
