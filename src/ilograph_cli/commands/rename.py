"""`rename` command registration."""

from __future__ import annotations

from pathlib import Path

import typer
from ruamel.yaml.comments import CommentedMap

from ilograph_cli.cli_options import diff_mode_option, file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.core.arg_models import RenameResourceArgs, RenameResourceIdArgs
from ilograph_cli.ops.resource_ops import rename_resource, rename_resource_id


def register(app: typer.Typer, *, guard: CliGuard, runner: MutationRunner) -> None:
    """Register rename subcommands."""

    @app.command("resource")
    def rename_resource_cmd(
        file_path: Path = file_option,
        resource_id: str = typer.Option(..., "--id", help="Resource id to rename."),
        name: str = typer.Option(..., "--name", help="New display name."),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview diff and validation results without writing.",
        ),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Rename resource name."""

        with guard:
            args = validate_payload(RenameResourceArgs, {"id": resource_id, "name": name})

            def mutate(document: CommentedMap) -> bool:
                return rename_resource(document, resource_id=args.id, new_name=args.name)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("resource-id")
    def rename_resource_id_cmd(
        file_path: Path = file_option,
        from_id: str = typer.Option(..., "--from", help="Existing resource id."),
        to_id: str = typer.Option(
            ...,
            "--to",
            help="New resource id (reference fields are rewritten).",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview diff and validation results without writing.",
        ),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Rename resource id + update references."""

        with guard:
            args = validate_payload(RenameResourceIdArgs, {"from": from_id, "to": to_id})

            def mutate(document: CommentedMap) -> bool:
                return rename_resource_id(document, old_id=args.from_, new_id=args.to)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
