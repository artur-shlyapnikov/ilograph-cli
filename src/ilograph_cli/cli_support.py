"""Shared CLI utilities."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from types import TracebackType
from typing import Literal, NoReturn, cast

import typer
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console
from ruamel.yaml.comments import CommentedMap

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.validators import validate_document
from ilograph_cli.io.diff import build_unified_diff, print_diff, summarize_diff
from ilograph_cli.io.yaml_io import (
    detect_format_profile,
    dump_document,
    load_document,
    read_text,
    write_text,
)

type DiffMode = Literal["full", "summary", "none"]
Mutator = Callable[[CommentedMap], bool | None]

_BLOCK_HEADER_STYLE_RE = re.compile(r":\s*([|>])\d*([+-]?)$")


def validate_payload[TModel: BaseModel](
    model_type: type[TModel], payload: Mapping[str, object]
) -> TModel:
    """Validate command payload against pydantic model."""

    try:
        return model_type.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError(
            _format_pydantic_validation_error(
                exc,
                header="invalid command arguments:",
            )
        ) from exc


def handle_error(console: Console, exc: Exception) -> NoReturn:
    """Render user-visible CLI error and exit non-zero."""

    console.print(f"[red]error:[/red] {exc}")
    console.print("[dim]hint:[/dim] run with `--help` for command usage.")
    raise typer.Exit(code=1)


class CliGuard(AbstractContextManager[None]):
    """Context manager for consistent command error handling."""

    def __init__(self, *, console: Console) -> None:
        self.console = console

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        del exc_type
        del traceback
        if exc is None:
            return False
        if isinstance(exc, (typer.Exit, KeyboardInterrupt)):
            return False
        if not isinstance(exc, Exception):
            return False
        handle_error(self.console, exc)


@dataclass(slots=True)
class MutationRunner:
    """Reusable read/mutate/diff/write flow for mutating commands."""

    console: Console
    diff_preview_limit: int = 120

    def run(
        self,
        *,
        file_path: Path,
        dry_run: bool,
        diff_mode: str,
        mutator: Mutator,
    ) -> None:
        before = read_text(file_path)
        format_profile = detect_format_profile(before)
        document = load_document(file_path, format_profile=format_profile)
        changed_hint = mutator(document)
        if changed_hint is False:
            self.console.print("no changes (document already matches requested state)")
            return

        _ensure_document_valid_for_write(document)
        after = dump_document(document, format_profile=format_profile)
        after = _restore_style_only_replacements(before, after)
        normalized_diff_mode = _normalize_diff_mode(diff_mode)

        changed = self._render_diff(before, after, file_path, diff_mode=normalized_diff_mode)
        if not changed:
            return
        if dry_run:
            self.console.print("dry-run: changes were not written")
            return

        write_text(file_path, after)
        self.console.print(f"updated: {file_path}")

    def _render_diff(self, before: str, after: str, path: Path, *, diff_mode: DiffMode) -> bool:
        if before == after:
            self.console.print("no changes (serialized YAML is unchanged)")
            return False

        diff_lines = build_unified_diff(before, after, str(path))
        summary = summarize_diff(diff_lines)

        if diff_mode == "none":
            self.console.print(
                f"changes: +{summary.added} -{summary.deleted} ({summary.hunks} hunks); "
                "diff hidden (--diff full to show)"
            )
            return True

        if diff_mode == "summary" and len(diff_lines) > self.diff_preview_limit:
            self.console.print(
                f"diff summary: +{summary.added} -{summary.deleted} "
                f"({summary.hunks} hunks); showing first {self.diff_preview_limit} lines"
            )
            print_diff(self.console, diff_lines[: self.diff_preview_limit])
            self.console.print("... diff truncated (use --diff full to print all)")
            return True

        print_diff(self.console, diff_lines)
        return True


def _normalize_diff_mode(mode: str) -> DiffMode:
    normalized = mode.strip().lower()
    if normalized not in {"full", "summary", "none"}:
        raise ValidationError(
            f"unknown diff mode: {mode} (expected: full|summary|none)"
        )
    return cast(DiffMode, normalized)


def _restore_style_only_replacements(before: str, after: str) -> str:
    if before == after:
        return after

    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = SequenceMatcher(a=before_lines, b=after_lines, autojunk=False)

    merged: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            merged.extend(before_lines[i1:i2])
            continue
        if tag == "replace":
            original_block = before_lines[i1:i2]
            emitted_block = after_lines[j1:j2]
            if _style_equivalent_block(original_block, emitted_block):
                merged.extend(original_block)
            else:
                merged.extend(emitted_block)
            continue
        if tag == "insert":
            merged.extend(after_lines[j1:j2])
            continue
        if tag == "delete":
            continue

    joined = "\n".join(merged)
    if after.endswith("\n"):
        return joined + "\n"
    return joined


def _style_equivalent_block(before_lines: list[str], after_lines: list[str]) -> bool:
    if len(before_lines) != len(after_lines):
        return False

    for before_line, after_line in zip(before_lines, after_lines, strict=True):
        if _normalize_style_line(before_line) != _normalize_style_line(after_line):
            return False
    return True


def _normalize_style_line(line: str) -> str:
    normalized = line.lstrip(" ")
    return _BLOCK_HEADER_STYLE_RE.sub(r": \1\2", normalized)


def _ensure_document_valid_for_write(document: CommentedMap) -> None:
    issues = validate_document(document, mode="strict").issues
    if not issues:
        return

    preview_limit = 8
    lines = [
        (
            "mutation would produce invalid document "
            f"({len(issues)} issue(s), strict mode):"
        )
    ]
    for issue in issues[:preview_limit]:
        lines.append(f"- {issue.code} at {issue.path}: {issue.message}")
    if len(issues) > preview_limit:
        lines.append(f"- ... and {len(issues) - preview_limit} more")
    raise ValidationError("\n".join(lines))


def _format_pydantic_validation_error(
    exc: PydanticValidationError,
    *,
    header: str,
) -> str:
    issues = exc.errors()
    if not issues:
        return header

    preview_limit = 8
    lines: list[str] = []
    for issue in issues[:preview_limit]:
        path = _format_error_location(issue.get("loc", ()))
        message = _normalize_issue_message(str(issue.get("msg", "invalid value")))
        lines.append(f"{path}: {message}" if path else message)

    if len(lines) == 1:
        return lines[0]

    output = [header, *[f"- {line}" for line in lines]]
    if len(issues) > preview_limit:
        output.append(f"- ... and {len(issues) - preview_limit} more")
    return "\n".join(output)


def _format_error_location(loc: object) -> str:
    if not isinstance(loc, tuple):
        return ""

    path = ""
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
            continue
        if not isinstance(part, str) or part in {"__root__", "__all__"}:
            continue
        if path:
            path += f".{part}"
        else:
            path = part
    return path


def _normalize_issue_message(message: str) -> str:
    normalized = message.strip()
    prefixes = ("Value error, ", "Assertion failed, ")
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix) :]
    return normalized
