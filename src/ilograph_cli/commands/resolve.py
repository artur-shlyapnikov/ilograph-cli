"""`resolve`/`find` command registration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table

from ilograph_cli.cli_options import file_option
from ilograph_cli.cli_support import CliGuard
from ilograph_cli.core.index import get_single_perspective
from ilograph_cli.core.reference_resolution import resolve_reference
from ilograph_cli.io.yaml_io import load_document


def register(app: typer.Typer, *, console: Console, guard: CliGuard) -> None:
    """Register `resolve`/`find` commands."""

    @app.command("resolve")
    @app.command("find")
    def resolve_cmd(
        file_path: Path = file_option,
        reference: str = typer.Option(
            ...,
            "--reference",
            "--ref",
            help="Reference expression to resolve (aliases, paths, wildcards).",
        ),
        perspective: str | None = typer.Option(
            None,
            "--perspective",
            help="Perspective id/name for alias context.",
        ),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable JSON output.",
        ),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap or truncate table columns.",
        ),
    ) -> None:
        """Inspect how a reference expression resolves."""

        with guard:
            document = load_document(file_path)
            resolved_perspective: str | None = None
            if perspective is not None and perspective.strip():
                resolved_perspective = get_single_perspective(
                    document,
                    perspective.strip(),
                ).identifier

            resolved_perspective, rows = resolve_reference(
                document,
                reference=reference,
                perspective=resolved_perspective,
            )

            if json_output:
                payload = {
                    "reference": reference,
                    "perspective": resolved_perspective,
                    "rows": [
                        {
                            "part": row.part,
                            "token": row.token,
                            "status": row.status,
                            "details": row.details,
                        }
                        for row in rows
                    ],
                }
                typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            perspective_label = resolved_perspective if resolved_perspective is not None else "-"
            table = Table(title=f"Resolve: {reference} (perspective: {perspective_label})")
            table.add_column("Part", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Token", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Status", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Details", overflow=overflow_mode, no_wrap=no_truncate)
            for row in rows:
                table.add_row(row.part, row.token, row.status, row.details)

            console.print(table)
