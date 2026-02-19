"""`alias` command registration."""

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
from ilograph_cli.core.normalize import normalize_required_str
from ilograph_cli.io.yaml_io import load_document
from ilograph_cli.ops.alias_ops import add_alias, edit_alias, list_aliases, remove_alias


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register alias subcommands."""

    @app.command("ls")
    @app.command("list")
    def alias_list_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap/truncate table columns",
        ),
    ) -> None:
        """List aliases in perspective."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            document = load_document(file_path)
            rows = list_aliases(document, perspective=resolved_perspective)

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
                console.print("no aliases")
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title=f"Aliases: {resolved_perspective}")
            table.add_column("Index", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Alias", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("For", overflow=overflow_mode, no_wrap=no_truncate)

            for row in rows:
                table.add_row(
                    str(row["index"]),
                    str(row["alias"]),
                    str(row["for"] or "-"),
                )
            console.print(table)
            console.print(f"total: {len(rows)}")

    @app.command("add")
    def alias_add_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        alias: str = typer.Option(..., "--alias"),
        alias_for: str = typer.Option(..., "--for"),
        index: int | None = typer.Option(
            None,
            "--index",
            help="Insert at 1-based position (default: append).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Add alias."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            resolved_alias = _normalize_required(alias, field_name="alias")
            resolved_for = _normalize_required(alias_for, field_name="for")

            def mutate(document: CommentedMap) -> bool:
                return add_alias(
                    document,
                    perspective=resolved_perspective,
                    alias=resolved_alias,
                    alias_for=resolved_for,
                    index_1_based=index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("edit")
    def alias_edit_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        alias: str = typer.Option(..., "--alias"),
        new_alias: str | None = typer.Option(None, "--new-alias"),
        new_for: str | None = typer.Option(None, "--new-for"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Edit alias."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            resolved_alias = _normalize_required(alias, field_name="alias")
            resolved_new_alias = (
                _normalize_required(new_alias, field_name="new_alias")
                if new_alias is not None
                else None
            )
            resolved_new_for = (
                _normalize_required(new_for, field_name="new_for")
                if new_for is not None
                else None
            )

            def mutate(document: CommentedMap) -> bool:
                return edit_alias(
                    document,
                    perspective=resolved_perspective,
                    alias=resolved_alias,
                    new_alias=resolved_new_alias,
                    new_for=resolved_new_for,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("remove")
    def alias_remove_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        alias: str = typer.Option(..., "--alias"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Remove alias."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            resolved_alias = _normalize_required(alias, field_name="alias")

            def mutate(document: CommentedMap) -> bool:
                return remove_alias(
                    document,
                    perspective=resolved_perspective,
                    alias=resolved_alias,
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
