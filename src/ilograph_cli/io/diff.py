"""Diff helpers."""

from __future__ import annotations

import re
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


@dataclass(slots=True)
class SectionDiff:
    """Per top-level section diff counts."""

    name: str
    added: int = 0
    deleted: int = 0


_TOP_LEVEL_SECTION_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(?:#.*)?$"
)
_DEFAULT_TOUCHED_SECTIONS: tuple[str, ...] = ("resources", "contexts", "perspectives")


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


def summarize_touched_sections(
    before: str,
    after: str,
    *,
    sections: tuple[str, ...] = _DEFAULT_TOUCHED_SECTIONS,
) -> list[SectionDiff]:
    """Summarize touched top-level sections by +/- line counts."""

    before_blocks = _extract_top_level_blocks(before)
    after_blocks = _extract_top_level_blocks(after)
    touched: list[SectionDiff] = []

    for section in sections:
        before_block = before_blocks.get(section, [])
        after_block = after_blocks.get(section, [])
        if before_block == after_block:
            continue

        section_diff = unified_diff(
            before_block,
            after_block,
            fromfile=f"a/{section}",
            tofile=f"b/{section}",
            lineterm="",
        )
        summary = summarize_diff(section_diff)
        touched.append(
            SectionDiff(
                name=section,
                added=summary.added,
                deleted=summary.deleted,
            )
        )
    return touched


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


def _extract_top_level_blocks(raw: str) -> dict[str, list[str]]:
    lines = raw.splitlines(keepends=False)
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if line.startswith(" "):
            continue
        match = _TOP_LEVEL_SECTION_LINE_RE.match(line)
        if match is None:
            continue
        starts.append((index, match.group("name")))

    if not starts:
        return {}

    blocks: dict[str, list[str]] = {}
    for idx, (start_index, name) in enumerate(starts):
        end_index = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        blocks[name] = lines[start_index:end_index]
    return blocks
