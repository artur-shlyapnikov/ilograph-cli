"""`fmt` command registration."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from ilograph_cli.cli_options import file_option
from ilograph_cli.cli_support import CliGuard
from ilograph_cli.core.errors import ValidationError
from ilograph_cli.io.yaml_io import load_document


def register(app: typer.Typer, *, console: Console, guard: CliGuard) -> None:
    """Register `fmt` command."""

    @app.command("fmt")
    def fmt_cmd(
        file_path: Path = file_option,
        stable: bool = typer.Option(
            False,
            "--stable",
            help="Required guard flag for stable round-trip formatting mode.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview only; validate/read without writing.",
        ),
    ) -> None:
        """Format YAML with stable round-trip emitter."""

        with guard:
            if not stable:
                raise ValidationError("only --stable is supported (pass --stable)")

            _ = load_document(file_path)
            console.print("no changes (stable formatter is intentionally no-op)")
            if dry_run:
                console.print("dry-run: changes were not written")
