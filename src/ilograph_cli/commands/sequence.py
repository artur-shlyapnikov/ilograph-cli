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
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.core.arg_models import (
    PerspectiveScopeArgs,
    SequenceAddArgs,
    SequenceEditArgs,
    SequenceRemoveArgs,
)
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
            args = validate_payload(PerspectiveScopeArgs, {"perspective": perspective})
            document = load_document(file_path)
            rows = list_sequence_steps(document, perspective=args.perspective)

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
            table = Table(title=f"Sequence: {args.perspective}")
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
            args = validate_payload(
                SequenceAddArgs,
                {
                    "perspective": perspective,
                    "to": to,
                    "to_and_back": to_and_back,
                    "to_async": to_async,
                    "restart_at": restart_at,
                    "label": label,
                    "description": description,
                    "bidirectional": bidirectional,
                    "color": color,
                    "index": index,
                    "start": start,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return add_sequence_step(
                    document,
                    perspective=args.perspective,
                    to=args.to,
                    to_and_back=args.to_and_back,
                    to_async=args.to_async,
                    restart_at=args.restart_at,
                    label=args.label,
                    description=args.description,
                    bidirectional=args.bidirectional,
                    color=args.color,
                    index_1_based=args.index,
                    start_if_missing=args.start,
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
            args = validate_payload(
                SequenceEditArgs,
                {
                    "perspective": perspective,
                    "index": index,
                    "to": to,
                    "to_and_back": to_and_back,
                    "to_async": to_async,
                    "restart_at": restart_at,
                    "label": label,
                    "description": description,
                    "bidirectional": bidirectional,
                    "color": color,
                    "clear_label": clear_label,
                    "clear_description": clear_description,
                    "clear_color": clear_color,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return edit_sequence_step(
                    document,
                    perspective=args.perspective,
                    index_1_based=args.index,
                    to=args.to,
                    to_and_back=args.to_and_back,
                    to_async=args.to_async,
                    restart_at=args.restart_at,
                    label=args.label,
                    description=args.description,
                    bidirectional=args.bidirectional,
                    color=args.color,
                    clear_label=args.clear_label,
                    clear_description=args.clear_description,
                    clear_color=args.clear_color,
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
            args = validate_payload(
                SequenceRemoveArgs,
                {"perspective": perspective, "index": index},
            )

            def mutate(document: CommentedMap) -> bool:
                return remove_sequence_step(
                    document,
                    perspective=args.perspective,
                    index_1_based=args.index,
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
