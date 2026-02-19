"""`impact` command registration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table

from ilograph_cli.cli_options import file_option
from ilograph_cli.cli_support import CliGuard
from ilograph_cli.core.impact import impact_for_resource
from ilograph_cli.io.yaml_io import load_document


def register(app: typer.Typer, *, console: Console, guard: CliGuard) -> None:
    """Register `impact` command."""

    @app.command("impact")
    def impact_cmd(
        file_path: Path = file_option,
        resource_id: str = typer.Option(
            ...,
            "--resource-id",
            help="Resource id to search for across references.",
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
        """Show where resource is used."""

        with guard:
            document = load_document(file_path)
            normalized_resource_id = resource_id.strip()
            hits = impact_for_resource(document, normalized_resource_id)

            if json_output:
                payload = {
                    "resourceId": normalized_resource_id,
                    "count": len(hits),
                    "hits": [
                        {
                            "perspective": hit.perspective,
                            "section": hit.section,
                            "field": hit.field,
                            "path": hit.path,
                            "value": hit.value,
                        }
                        for hit in hits
                    ],
                }
                typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
                return

            if not hits:
                console.print(
                    f"no references found for: {normalized_resource_id} "
                    "(resource may be unused or misspelled)"
                )
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title=f"Impact for {normalized_resource_id} ({len(hits)} hits)")
            table.add_column("Perspective", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Section", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Field", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Path", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Value", overflow=overflow_mode, no_wrap=no_truncate)

            for hit in hits:
                table.add_row(hit.perspective or "-", hit.section, hit.field, hit.path, hit.value)
            console.print(table)
