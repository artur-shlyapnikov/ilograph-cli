"""Shared CLI utilities."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
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
from ilograph_cli.io.diff import (
    SectionDiff,
    build_unified_diff,
    print_diff,
    summarize_diff,
    summarize_touched_sections,
)
from ilograph_cli.io.yaml_io import (
    detect_format_profile,
    dump_document,
    file_lock,
    load_document,
    read_text,
    write_text_atomic,
)
from ilograph_cli.io.yaml_style import (
    restore_document_anchors,
    restore_style_only_replacements,
    snapshot_document_anchors,
)

type DiffMode = Literal["full", "summary", "none"]
Mutator = Callable[[CommentedMap], bool | None]


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
    lock_wait_seconds: float = 0.0

    def run(
        self,
        *,
        file_path: Path,
        dry_run: bool,
        diff_mode: str,
        mutator: Mutator,
    ) -> None:
        normalized_diff_mode = _normalize_diff_mode(diff_mode)
        if dry_run:
            self._run_once(
                file_path=file_path,
                dry_run=True,
                diff_mode=normalized_diff_mode,
                mutator=mutator,
            )
            return

        with file_lock(file_path, timeout_seconds=self.lock_wait_seconds):
            self._run_once(
                file_path=file_path,
                dry_run=False,
                diff_mode=normalized_diff_mode,
                mutator=mutator,
            )

    def _run_once(
        self,
        *,
        file_path: Path,
        dry_run: bool,
        diff_mode: DiffMode,
        mutator: Mutator,
    ) -> None:
        before = read_text(file_path)
        format_profile = detect_format_profile(before)
        document = load_document(file_path, format_profile=format_profile)
        anchor_snapshot = snapshot_document_anchors(document)
        changed_hint = mutator(document)
        if changed_hint is False:
            self.console.print("no changes (document already matches requested state)")
            return

        restore_document_anchors(document, anchor_snapshot)
        _ensure_document_valid_for_write(document)
        after = dump_document(document, format_profile=format_profile)
        after = restore_style_only_replacements(before, after)
        changed = self._render_diff(before, after, file_path, diff_mode=diff_mode)
        if not changed:
            return
        if dry_run:
            self.console.print("dry-run: changes were not written")
            return

        write_text_atomic(file_path, after, expected_before=before)
        self.console.print(f"updated: {file_path}")

    def _render_diff(self, before: str, after: str, path: Path, *, diff_mode: DiffMode) -> bool:
        if before == after:
            self.console.print("no changes (serialized YAML is unchanged)")
            return False

        diff_lines = build_unified_diff(before, after, str(path))
        summary = summarize_diff(diff_lines)
        touched_sections = summarize_touched_sections(before, after)
        section_summary = _format_touched_sections(touched_sections)

        if diff_mode == "none":
            self.console.print(
                f"changes: +{summary.added} -{summary.deleted} ({summary.hunks} hunks); "
                f"{section_summary}; diff hidden (--diff full to show)"
            )
            return True

        if diff_mode == "summary" and len(diff_lines) > self.diff_preview_limit:
            self.console.print(
                f"diff summary: +{summary.added} -{summary.deleted} "
                f"({summary.hunks} hunks); {section_summary}; "
                f"showing first {self.diff_preview_limit} lines"
            )
            print_diff(self.console, diff_lines[: self.diff_preview_limit])
            self.console.print("... diff truncated (use --diff full to print all)")
            return True

        self.console.print(
            f"diff summary: +{summary.added} -{summary.deleted} "
            f"({summary.hunks} hunks); {section_summary}"
        )
        print_diff(self.console, diff_lines)
        return True


def _normalize_diff_mode(mode: str) -> DiffMode:
    normalized = mode.strip().lower()
    if normalized not in {"full", "summary", "none"}:
        raise ValidationError(
            f"unknown diff mode: {mode} (expected: full|summary|none)"
        )
    return cast(DiffMode, normalized)


def _format_touched_sections(sections: list[SectionDiff]) -> str:
    if not sections:
        return "touched sections: none"
    rendered = ", ".join(
        f"{section.name}(+{section.added}/-{section.deleted})"
        for section in sections
    )
    return f"touched sections: {rendered}"


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
