"""Diff helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from difflib import unified_diff

from rich.console import Console
from rich.text import Text


@dataclass(slots=True)
class DiffSummary:
    """Small diff stats payload for CLI UX."""

    added: int = 0
    deleted: int = 0
    hunks: int = 0


def build_unified_diff(before: str, after: str, path: str) -> list[str]:
    """Build unified diff lines."""

    normalized_path = _normalize_path_for_diff(path)
    return list(
        unified_diff(
            before.splitlines(keepends=False),
            after.splitlines(keepends=False),
            fromfile=f"a/{normalized_path}",
            tofile=f"b/{normalized_path}",
            lineterm="",
        )
    )


def summarize_diff(lines: Iterable[str]) -> DiffSummary:
    """Collect +/-, hunk count from unified diff output."""

    summary = DiffSummary()
    for line in lines:
        if line.startswith("@@"):
            summary.hunks += 1
            continue
        if line.startswith("+++"):
            continue
        if line.startswith("---"):
            continue
        if line.startswith("+"):
            summary.added += 1
            continue
        if line.startswith("-"):
            summary.deleted += 1
    return summary


def print_diff(console: Console, lines: Iterable[str]) -> None:
    """Print colored diff."""

    for line in lines:
        style = "white"
        if line.startswith(("+++", "---")):
            style = "bold"
        elif line.startswith("@@"):
            style = "cyan"
        elif line.startswith("+"):
            style = "green"
        elif line.startswith("-"):
            style = "red"
        console.print(Text(line, style=style))


def _normalize_path_for_diff(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/"):
        normalized = normalized.lstrip("/")
    return normalized or path
