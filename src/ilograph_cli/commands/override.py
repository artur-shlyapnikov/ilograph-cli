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
from ilograph_cli.cli_support import CliGuard, MutationRunner
from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.normalize import normalize_required_str
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
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            document = load_document(file_path)
            rows = list_overrides(document, perspective=resolved_perspective)

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
            table = Table(title=f"Overrides: {resolved_perspective}")
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
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            resolved_resource_id = _normalize_required(resource_id, field_name="resource_id")
            resolved_parent_id = (
                _normalize_required(parent_id, field_name="parent_id")
                if parent_id is not None
                else None
            )

            def mutate(document: CommentedMap) -> bool:
                return add_override(
                    document,
                    perspective=resolved_perspective,
                    resource_id=resolved_resource_id,
                    parent_id=resolved_parent_id,
                    scale=scale,
                    index_1_based=index,
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
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            resolved_resource_id = _normalize_required(resource_id, field_name="resource_id")
            resolved_new_resource_id = (
                _normalize_required(new_resource_id, field_name="new_resource_id")
                if new_resource_id is not None
                else None
            )
            resolved_parent_id = (
                _normalize_required(parent_id, field_name="parent_id")
                if parent_id is not None
                else None
            )

            def mutate(document: CommentedMap) -> bool:
                return edit_override(
                    document,
                    perspective=resolved_perspective,
                    resource_id=resolved_resource_id,
                    new_resource_id=resolved_new_resource_id,
                    parent_id=resolved_parent_id,
                    scale=scale,
                    clear_parent_id=clear_parent_id,
                    clear_scale=clear_scale,
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
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            resolved_resource_id = _normalize_required(resource_id, field_name="resource_id")

            def mutate(document: CommentedMap) -> bool:
                return remove_override(
                    document,
                    perspective=resolved_perspective,
                    resource_id=resolved_resource_id,
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
