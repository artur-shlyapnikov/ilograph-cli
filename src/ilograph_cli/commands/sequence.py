"""`sequence` command registration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table
from ruamel.yaml.comments import CommentedMap

from ilograph_cli.cli_options import diff_mode_option, file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner
from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.normalize import normalize_optional_str, normalize_required_str
from ilograph_cli.io.yaml_io import load_document
from ilograph_cli.ops.sequence_ops import (
    add_sequence_step,
    edit_sequence_step,
    list_sequence_steps,
    remove_sequence_step,
)


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register sequence subcommands."""

    @app.command("ls")
    @app.command("list")
    def sequence_list_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap/truncate table columns",
        ),
    ) -> None:
        """List sequence steps."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            document = load_document(file_path)
            rows = list_sequence_steps(document, perspective=resolved_perspective)

            if json_output:
                typer.echo(
                    json.dumps(
                        {"count": len(rows), "rows": rows},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return

            if not rows:
                console.print("no sequence steps")
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title=f"Sequence: {resolved_perspective}")
            table.add_column("Index", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Action", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Target", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Label", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Bidirectional", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Color", overflow=overflow_mode, no_wrap=no_truncate)

            for row in rows:
                action, target = _action_and_target(row)
                table.add_row(
                    str(row["index"]),
                    action,
                    target,
                    str(row["label"] or "-"),
                    "yes" if row["bidirectional"] else "no",
                    str(row["color"] or "-"),
                )
            console.print(table)
            console.print(f"total: {len(rows)}")

    @app.command("add")
    def sequence_add_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        to: str | None = typer.Option(None, "--to"),
        to_and_back: str | None = typer.Option(None, "--to-and-back"),
        to_async: str | None = typer.Option(None, "--to-async"),
        restart_at: str | None = typer.Option(None, "--restart-at"),
        label: str | None = typer.Option(None, "--label"),
        description: str | None = typer.Option(None, "--description"),
        bidirectional: bool | None = typer.Option(
            None,
            "--bidirectional/--no-bidirectional",
        ),
        color: str | None = typer.Option(None, "--color"),
        index: int | None = typer.Option(
            None,
            "--index",
            help="Insert at 1-based position (default: append).",
        ),
        start: str | None = typer.Option(
            None,
            "--start",
            help="Create sequence with this start when perspective has no sequence.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Add sequence step."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")

            def mutate(document: CommentedMap) -> bool:
                return add_sequence_step(
                    document,
                    perspective=resolved_perspective,
                    to=_normalize_optional(to, field_name="to"),
                    to_and_back=_normalize_optional(to_and_back, field_name="to_and_back"),
                    to_async=_normalize_optional(to_async, field_name="to_async"),
                    restart_at=_normalize_optional(restart_at, field_name="restart_at"),
                    label=_normalize_optional(label, field_name="label"),
                    description=_normalize_optional(description, field_name="description"),
                    bidirectional=bidirectional,
                    color=_normalize_optional(color, field_name="color"),
                    index_1_based=index,
                    start_if_missing=_normalize_optional(start, field_name="start"),
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("edit")
    def sequence_edit_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        index: int = typer.Option(..., "--index", help="1-based step index"),
        to: str | None = typer.Option(None, "--to"),
        to_and_back: str | None = typer.Option(None, "--to-and-back"),
        to_async: str | None = typer.Option(None, "--to-async"),
        restart_at: str | None = typer.Option(None, "--restart-at"),
        label: str | None = typer.Option(None, "--label"),
        description: str | None = typer.Option(None, "--description"),
        bidirectional: bool | None = typer.Option(
            None,
            "--bidirectional/--no-bidirectional",
        ),
        color: str | None = typer.Option(None, "--color"),
        clear_label: bool = typer.Option(False, "--clear-label"),
        clear_description: bool = typer.Option(False, "--clear-description"),
        clear_color: bool = typer.Option(False, "--clear-color"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Edit sequence step."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")

            def mutate(document: CommentedMap) -> bool:
                return edit_sequence_step(
                    document,
                    perspective=resolved_perspective,
                    index_1_based=index,
                    to=_normalize_optional(to, field_name="to"),
                    to_and_back=_normalize_optional(to_and_back, field_name="to_and_back"),
                    to_async=_normalize_optional(to_async, field_name="to_async"),
                    restart_at=_normalize_optional(restart_at, field_name="restart_at"),
                    label=_normalize_optional(label, field_name="label"),
                    description=_normalize_optional(description, field_name="description"),
                    bidirectional=bidirectional,
                    color=_normalize_optional(color, field_name="color"),
                    clear_label=clear_label,
                    clear_description=clear_description,
                    clear_color=clear_color,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("remove")
    def sequence_remove_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        index: int = typer.Option(..., "--index", help="1-based step index"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Remove sequence step."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")

            def mutate(document: CommentedMap) -> bool:
                return remove_sequence_step(
                    document,
                    perspective=resolved_perspective,
                    index_1_based=index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )


def _action_and_target(row: dict[str, object]) -> tuple[str, str]:
    for key in ("to", "toAndBack", "toAsync", "restartAt"):
        value = row.get(key)
        if isinstance(value, str):
            return key, value
    return "-", "-"


def _normalize_required(value: str, *, field_name: str) -> str:
    try:
        return normalize_required_str(value, field_name=field_name)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def _normalize_optional(value: str | None, *, field_name: str) -> str | None:
    try:
        return normalize_optional_str(value, field_name=field_name, empty_is_none=True)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
