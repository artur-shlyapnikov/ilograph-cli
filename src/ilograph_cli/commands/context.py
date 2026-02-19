"""`context` command registration."""

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
from ilograph_cli.ops.context_ops import (
    copy_context,
    create_context,
    delete_context,
    list_contexts,
    rename_context,
    reorder_context,
)


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register context subcommands."""

    @app.command("ls")
    @app.command("list")
    def context_list_cmd(
        file_path: Path = file_option,
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap/truncate table columns",
        ),
    ) -> None:
        """List contexts."""

        with guard:
            document = load_document(file_path)
            rows = list_contexts(document)

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
                console.print("no contexts")
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title="Contexts")
            table.add_column("Index", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Name", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Extends", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Hidden", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Roots", overflow=overflow_mode, no_wrap=no_truncate)

            for row in rows:
                table.add_row(
                    str(row["index"]),
                    str(row["name"]),
                    str(row["extends"] or "-"),
                    "yes" if row["hidden"] else "no",
                    "yes" if row["hasRoots"] else "no",
                )
            console.print(table)
            console.print(f"total: {len(rows)}")

    @app.command("create")
    def context_create_cmd(
        file_path: Path = file_option,
        name: str = typer.Option(..., "--name"),
        extends: str | None = typer.Option(None, "--extends"),
        hidden: bool | None = typer.Option(
            None,
            "--hidden/--visible",
            help="Set hidden flag explicitly.",
        ),
        index: int | None = typer.Option(
            None,
            "--index",
            help="Insert at 1-based position (default: append).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Create context."""

        with guard:
            resolved_name = _normalize_required(name, field_name="name")
            resolved_extends = _normalize_optional(extends, field_name="extends")

            def mutate(document: CommentedMap) -> bool:
                return create_context(
                    document,
                    name=resolved_name,
                    extends=resolved_extends,
                    hidden=hidden,
                    index_1_based=index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("rename")
    def context_rename_cmd(
        file_path: Path = file_option,
        name: str = typer.Option(..., "--name", help="Current context name."),
        new_name: str = typer.Option(..., "--new-name"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Rename context."""

        with guard:
            resolved_name = _normalize_required(name, field_name="name")
            resolved_new_name = _normalize_required(new_name, field_name="new_name")

            def mutate(document: CommentedMap) -> bool:
                return rename_context(document, name=resolved_name, new_name=resolved_new_name)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("delete")
    def context_delete_cmd(
        file_path: Path = file_option,
        name: str = typer.Option(..., "--name"),
        force: bool = typer.Option(
            False,
            "--force",
            help="Also remove extends references from other contexts.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Delete context."""

        with guard:
            resolved_name = _normalize_required(name, field_name="name")

            def mutate(document: CommentedMap) -> bool:
                return delete_context(document, name=resolved_name, force=force)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("reorder")
    def context_reorder_cmd(
        file_path: Path = file_option,
        name: str = typer.Option(..., "--name"),
        index: int = typer.Option(..., "--index", help="Target 1-based index."),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Reorder context."""

        with guard:
            resolved_name = _normalize_required(name, field_name="name")

            def mutate(document: CommentedMap) -> bool:
                return reorder_context(document, name=resolved_name, index_1_based=index)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("copy")
    def context_copy_cmd(
        file_path: Path = file_option,
        name: str = typer.Option(..., "--name", help="Source context name."),
        new_name: str = typer.Option(..., "--new-name"),
        index: int | None = typer.Option(
            None,
            "--index",
            help="Insert at 1-based position (default: append).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Copy context."""

        with guard:
            resolved_name = _normalize_required(name, field_name="name")
            resolved_new_name = _normalize_required(new_name, field_name="new_name")

            def mutate(document: CommentedMap) -> bool:
                return copy_context(
                    document,
                    name=resolved_name,
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
