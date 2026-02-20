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
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.core.arg_models import (
    ContextCopyArgs,
    ContextCreateArgs,
    ContextDeleteArgs,
    ContextRenameArgs,
    ContextReorderArgs,
)
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
            args = validate_payload(
                ContextCreateArgs,
                {
                    "name": name,
                    "extends": extends,
                    "hidden": hidden,
                    "index": index,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return create_context(
                    document,
                    name=args.name,
                    extends=args.extends,
                    hidden=args.hidden,
                    index_1_based=args.index,
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
            args = validate_payload(
                ContextRenameArgs,
                {"name": name, "new_name": new_name},
            )

            def mutate(document: CommentedMap) -> bool:
                return rename_context(document, name=args.name, new_name=args.new_name)

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
            args = validate_payload(ContextDeleteArgs, {"name": name, "force": force})

            def mutate(document: CommentedMap) -> bool:
                return delete_context(document, name=args.name, force=args.force)

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
            args = validate_payload(ContextReorderArgs, {"name": name, "index": index})

            def mutate(document: CommentedMap) -> bool:
                return reorder_context(document, name=args.name, index_1_based=args.index)

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
            args = validate_payload(
                ContextCopyArgs,
                {"name": name, "new_name": new_name, "index": index},
            )

            def mutate(document: CommentedMap) -> bool:
                return copy_context(
                    document,
                    name=args.name,
                    new_name=args.new_name,
                    index_1_based=args.index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
