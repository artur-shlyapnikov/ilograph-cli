"""`walkthrough` command registration."""

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
from ilograph_cli.ops.walkthrough_ops import (
    add_walkthrough_slide,
    edit_walkthrough_slide,
    list_walkthrough_slides,
    remove_walkthrough_slide,
)


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register walkthrough subcommands."""

    @app.command("ls")
    @app.command("list")
    def walkthrough_list_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap/truncate table columns",
        ),
    ) -> None:
        """List walkthrough slides."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")
            document = load_document(file_path)
            rows = list_walkthrough_slides(document, perspective=resolved_perspective)

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
                console.print("no walkthrough slides")
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title=f"Walkthrough: {resolved_perspective}")
            table.add_column("Index", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Text", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Select", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Expand", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Highlight", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Hide", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Detail", overflow=overflow_mode, no_wrap=no_truncate)

            for row in rows:
                table.add_row(
                    str(row["index"]),
                    str(row["text"] or "-"),
                    str(row["select"] or "-"),
                    str(row["expand"] or "-"),
                    str(row["highlight"] or "-"),
                    str(row["hide"] or "-"),
                    str(row["detail"] if row["detail"] is not None else "-"),
                )
            console.print(table)
            console.print(f"total: {len(rows)}")

    @app.command("add")
    def walkthrough_add_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        text: str | None = typer.Option(None, "--text"),
        select: str | None = typer.Option(None, "--select"),
        expand: str | None = typer.Option(None, "--expand"),
        highlight: str | None = typer.Option(None, "--highlight"),
        hide: str | None = typer.Option(None, "--hide"),
        detail: float | None = typer.Option(None, "--detail"),
        index: int | None = typer.Option(
            None,
            "--index",
            help="Insert at 1-based position (default: append).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Add walkthrough slide."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")

            def mutate(document: CommentedMap) -> bool:
                return add_walkthrough_slide(
                    document,
                    perspective=resolved_perspective,
                    text=_normalize_optional(text, field_name="text"),
                    select=_normalize_optional(select, field_name="select"),
                    expand=_normalize_optional(expand, field_name="expand"),
                    highlight=_normalize_optional(highlight, field_name="highlight"),
                    hide=_normalize_optional(hide, field_name="hide"),
                    detail=detail,
                    index_1_based=index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("edit")
    def walkthrough_edit_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        index: int = typer.Option(..., "--index", help="1-based slide index"),
        text: str | None = typer.Option(None, "--text"),
        select: str | None = typer.Option(None, "--select"),
        expand: str | None = typer.Option(None, "--expand"),
        highlight: str | None = typer.Option(None, "--highlight"),
        hide: str | None = typer.Option(None, "--hide"),
        detail: float | None = typer.Option(None, "--detail"),
        clear_text: bool = typer.Option(False, "--clear-text"),
        clear_select: bool = typer.Option(False, "--clear-select"),
        clear_expand: bool = typer.Option(False, "--clear-expand"),
        clear_highlight: bool = typer.Option(False, "--clear-highlight"),
        clear_hide: bool = typer.Option(False, "--clear-hide"),
        clear_detail: bool = typer.Option(False, "--clear-detail"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Edit walkthrough slide."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")

            def mutate(document: CommentedMap) -> bool:
                return edit_walkthrough_slide(
                    document,
                    perspective=resolved_perspective,
                    index_1_based=index,
                    text=_normalize_optional(text, field_name="text"),
                    select=_normalize_optional(select, field_name="select"),
                    expand=_normalize_optional(expand, field_name="expand"),
                    highlight=_normalize_optional(highlight, field_name="highlight"),
                    hide=_normalize_optional(hide, field_name="hide"),
                    detail=detail,
                    clear_text=clear_text,
                    clear_select=clear_select,
                    clear_expand=clear_expand,
                    clear_highlight=clear_highlight,
                    clear_hide=clear_hide,
                    clear_detail=clear_detail,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("remove")
    def walkthrough_remove_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        index: int = typer.Option(..., "--index", help="1-based slide index"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Remove walkthrough slide."""

        with guard:
            resolved_perspective = _normalize_required(perspective, field_name="perspective")

            def mutate(document: CommentedMap) -> bool:
                return remove_walkthrough_slide(
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
