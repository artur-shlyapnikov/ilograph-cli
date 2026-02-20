"""`override` command registration."""

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
    OverrideAddArgs,
    OverrideEditArgs,
    OverrideRemoveArgs,
    PerspectiveScopeArgs,
)
from ilograph_cli.io.yaml_io import load_document
from ilograph_cli.ops.override_ops import (
    add_override,
    edit_override,
    list_overrides,
    remove_override,
)


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register override subcommands."""

    @app.command("ls")
    @app.command("list")
    def override_list_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap/truncate table columns",
        ),
    ) -> None:
        """List overrides in perspective."""

        with guard:
            args = validate_payload(PerspectiveScopeArgs, {"perspective": perspective})
            document = load_document(file_path)
            rows = list_overrides(document, perspective=args.perspective)

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
                console.print("no overrides")
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title=f"Overrides: {args.perspective}")
            table.add_column("Index", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Resource", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Parent", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Scale", overflow=overflow_mode, no_wrap=no_truncate)

            for row in rows:
                table.add_row(
                    str(row["index"]),
                    str(row["resourceId"]),
                    str(row["parentId"] or "-"),
                    str(row["scale"] if row["scale"] is not None else "-"),
                )
            console.print(table)
            console.print(f"total: {len(rows)}")

    @app.command("add")
    def override_add_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        resource_id: str = typer.Option(..., "--resource-id"),
        parent_id: str | None = typer.Option(None, "--parent-id"),
        scale: float | None = typer.Option(None, "--scale"),
        index: int | None = typer.Option(
            None,
            "--index",
            help="Insert at 1-based position (default: append).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Add override."""

        with guard:
            args = validate_payload(
                OverrideAddArgs,
                {
                    "perspective": perspective,
                    "resource_id": resource_id,
                    "parent_id": parent_id,
                    "scale": scale,
                    "index": index,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return add_override(
                    document,
                    perspective=args.perspective,
                    resource_id=args.resource_id,
                    parent_id=args.parent_id,
                    scale=args.scale,
                    index_1_based=args.index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("edit")
    def override_edit_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        resource_id: str = typer.Option(..., "--resource-id"),
        new_resource_id: str | None = typer.Option(None, "--new-resource-id"),
        parent_id: str | None = typer.Option(None, "--parent-id"),
        scale: float | None = typer.Option(None, "--scale"),
        clear_parent_id: bool = typer.Option(False, "--clear-parent-id"),
        clear_scale: bool = typer.Option(False, "--clear-scale"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Edit override."""

        with guard:
            args = validate_payload(
                OverrideEditArgs,
                {
                    "perspective": perspective,
                    "resource_id": resource_id,
                    "new_resource_id": new_resource_id,
                    "parent_id": parent_id,
                    "scale": scale,
                    "clear_parent_id": clear_parent_id,
                    "clear_scale": clear_scale,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return edit_override(
                    document,
                    perspective=args.perspective,
                    resource_id=args.resource_id,
                    new_resource_id=args.new_resource_id,
                    parent_id=args.parent_id,
                    scale=args.scale,
                    clear_parent_id=args.clear_parent_id,
                    clear_scale=args.clear_scale,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("remove")
    def override_remove_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        resource_id: str = typer.Option(..., "--resource-id"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Remove override."""

        with guard:
            args = validate_payload(
                OverrideRemoveArgs,
                {
                    "perspective": perspective,
                    "resource_id": resource_id,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return remove_override(
                    document,
                    perspective=args.perspective,
                    resource_id=args.resource_id,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
