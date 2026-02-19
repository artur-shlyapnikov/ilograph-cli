"""`move` command registration."""

from __future__ import annotations

from pathlib import Path

import typer
from ruamel.yaml.comments import CommentedMap

from ilograph_cli.cli_options import diff_mode_option, file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.core.arg_models import MoveResourceArgs
from ilograph_cli.ops.resource_ops import move_resource


def register(app: typer.Typer, *, guard: CliGuard, runner: MutationRunner) -> None:
    """Register move subcommands."""

    @app.command("resource")
    def move_resource_cmd(
        file_path: Path = file_option,
        resource_id: str = typer.Option(..., "--id", help="Resource id to move."),
        new_parent: str = typer.Option(
            ...,
            "--new-parent",
            help="Destination parent resource id.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview diff and validation results without writing.",
        ),
        inherit_style_from_parent: bool = typer.Option(
            False,
            "--inherit-style-from-parent/--keep-style",
            help=(
                "Drop moved resource `style` so it inherits destination parent style "
                "(default: --keep-style)."
            ),
        ),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Move resource subtree."""

        with guard:
            args = validate_payload(
                MoveResourceArgs,
                {
                    "id": resource_id,
                    "new_parent": new_parent,
                    "inherit_style_from_parent": inherit_style_from_parent,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return move_resource(
                    document,
                    resource_id=args.id,
                    new_parent_id=args.new_parent,
                    inherit_style_from_parent=args.inherit_style_from_parent,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
