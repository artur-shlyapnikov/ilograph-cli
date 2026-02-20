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
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.core.arg_models import (
    AliasAddArgs,
    AliasEditArgs,
    AliasRemoveArgs,
    PerspectiveScopeArgs,
)
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
            args = validate_payload(PerspectiveScopeArgs, {"perspective": perspective})
            document = load_document(file_path)
            rows = list_aliases(document, perspective=args.perspective)

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
            table = Table(title=f"Aliases: {args.perspective}")
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
            args = validate_payload(
                AliasAddArgs,
                {
                    "perspective": perspective,
                    "alias": alias,
                    "for": alias_for,
                    "index": index,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return add_alias(
                    document,
                    perspective=args.perspective,
                    alias=args.alias,
                    alias_for=args.alias_for,
                    index_1_based=args.index,
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
            args = validate_payload(
                AliasEditArgs,
                {
                    "perspective": perspective,
                    "alias": alias,
                    "new_alias": new_alias,
                    "new_for": new_for,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return edit_alias(
                    document,
                    perspective=args.perspective,
                    alias=args.alias,
                    new_alias=args.new_alias,
                    new_for=args.new_for,
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
            args = validate_payload(
                AliasRemoveArgs,
                {
                    "perspective": perspective,
                    "alias": alias,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return remove_alias(
                    document,
                    perspective=args.perspective,
                    alias=args.alias,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
