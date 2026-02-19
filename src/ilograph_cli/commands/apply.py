"""`apply` command registration."""

from __future__ import annotations

from pathlib import Path

import typer
from ruamel.yaml.comments import CommentedMap

from ilograph_cli.cli_options import diff_mode_option, file_option, ops_file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner
from ilograph_cli.core.ops_models import parse_ops_payload
from ilograph_cli.io.yaml_io import load_any_yaml
from ilograph_cli.ops.apply_ops import apply_ops


def register(app: typer.Typer, *, guard: CliGuard, runner: MutationRunner) -> None:
    """Register `apply` command."""

    @app.command("apply")
    def apply_cmd(
        file_path: Path = file_option,
        ops_file: Path = ops_file_option,
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview diff and validation results without writing.",
        ),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Apply ops.yaml transaction."""

        with guard:
            payload = load_any_yaml(ops_file)
            parsed = parse_ops_payload(payload)

            def mutate(document: CommentedMap) -> bool:
                return apply_ops(document, parsed)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
