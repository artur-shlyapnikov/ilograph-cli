"""`perspective` command registration."""

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
from ilograph_cli.ops.perspective_ops import (
    copy_perspective,
    create_perspective,
    delete_perspective,
    list_perspectives,
    rename_perspective,
    reorder_perspective,
)


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register perspective subcommands."""

    @app.command("ls")
    @app.command("list")
    def perspective_list_cmd(
        file_path: Path = file_option,
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap/truncate table columns",
        ),
    ) -> None:
        """List perspectives."""

        with guard:
            document = load_document(file_path)
            rows = list_perspectives(document)

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
                console.print("no perspectives")
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title="Perspectives")
            table.add_column("Index", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Identifier", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Name", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Extends", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Orientation", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Relations", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Sequence", overflow=overflow_mode, no_wrap=no_truncate)

            for row in rows:
                table.add_row(
                    str(row["index"]),
                    str(row["identifier"]),
                    str(row["name"] or "-"),
                    str(row["extends"] or "-"),
                    str(row["orientation"] or "-"),
                    "yes" if row["hasRelations"] else "no",
                    "yes" if row["hasSequence"] else "no",
                )
            console.print(table)
            console.print(f"total: {len(rows)}")

    @app.command("create")
    def perspective_create_cmd(
        file_path: Path = file_option,
        perspective_id: str = typer.Option(..., "--id"),
        name: str | None = typer.Option(
            None,
            "--name",
            help="Display name (default: same as --id).",
        ),
        extends: str | None = typer.Option(None, "--extends"),
        orientation: str | None = typer.Option(None, "--orientation"),
        index: int | None = typer.Option(
            None,
            "--index",
            help="Insert at 1-based position (default: append).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Create perspective."""

        with guard:
            resolved_id = _normalize_required(perspective_id, field_name="id")
            resolved_name = _normalize_optional(name, field_name="name") or resolved_id
            resolved_extends = _normalize_optional(extends, field_name="extends")
            resolved_orientation = _normalize_optional(orientation, field_name="orientation")

            def mutate(document: CommentedMap) -> bool:
                return create_perspective(
                    document,
                    perspective_id=resolved_id,
                    name=resolved_name,
                    extends=resolved_extends,
                    orientation=resolved_orientation,
                    index_1_based=index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("rename")
    def perspective_rename_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--id", help="Current perspective id/name."),
        new_id: str | None = typer.Option(None, "--new-id"),
        new_name: str | None = typer.Option(None, "--new-name"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Rename perspective id/name."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="id")
            resolved_new_id = _normalize_optional(new_id, field_name="new_id")
            resolved_new_name = _normalize_optional(new_name, field_name="new_name")

            def mutate(document: CommentedMap) -> bool:
                return rename_perspective(
                    document,
                    perspective=resolved_perspective,
                    new_id=resolved_new_id,
                    new_name=resolved_new_name,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("delete")
    def perspective_delete_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--id", help="Perspective id/name."),
        force: bool = typer.Option(
            False,
            "--force",
            help="Also remove extends references from other perspectives.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Delete perspective."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="id")

            def mutate(document: CommentedMap) -> bool:
                return delete_perspective(document, perspective=resolved_perspective, force=force)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("reorder")
    def perspective_reorder_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--id", help="Perspective id/name."),
        index: int = typer.Option(..., "--index", help="Target 1-based index."),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Reorder perspective."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="id")

            def mutate(document: CommentedMap) -> bool:
                return reorder_perspective(
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

    @app.command("copy")
    def perspective_copy_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--id", help="Source perspective id/name."),
        new_id: str = typer.Option(..., "--new-id"),
        new_name: str | None = typer.Option(None, "--new-name"),
        index: int | None = typer.Option(
            None,
            "--index",
            help="Insert at 1-based position (default: append).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Copy perspective."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="id")
            resolved_new_id = _normalize_required(new_id, field_name="new_id")
            resolved_new_name = _normalize_optional(new_name, field_name="new_name")

            def mutate(document: CommentedMap) -> bool:
                return copy_perspective(
                    document,
                    perspective=resolved_perspective,
                    new_id=resolved_new_id,
                    new_name=resolved_new_name,
                    index_1_based=index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )


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
