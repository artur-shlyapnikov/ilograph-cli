"""`group` command registration."""

from __future__ import annotations

from pathlib import Path

import typer
from ruamel.yaml.comments import CommentedMap

from ilograph_cli.cli_options import diff_mode_option, file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.core.arg_models import GroupCreateArgs, MoveManyArgs
from ilograph_cli.ops.group_ops import create_group, move_many


def register(app: typer.Typer, *, guard: CliGuard, runner: MutationRunner) -> None:
    """Register group subcommands."""

    @app.command("create")
    def group_create_cmd(
        file_path: Path = file_option,
        group_id: str = typer.Option(..., "--id", help="New group resource id."),
        name: str = typer.Option(..., "--name", help="Group display name."),
        parent: str = typer.Option(
            ...,
            "--parent",
            help="Parent resource id, or 'none' to place group at root.",
        ),
        subtitle: str | None = typer.Option(
            None,
            "--subtitle",
            help="Optional group subtitle.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview diff and validation results without writing.",
        ),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Create group resource."""

        with guard:
            args = validate_payload(
                GroupCreateArgs,
                {
                    "id": group_id,
                    "name": name,
                    "parent": parent,
                    "subtitle": subtitle,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return create_group(
                    document,
                    group_id=args.id,
                    name=args.name,
                    parent_id=args.parent,
                    subtitle=args.subtitle,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("move-many")
    def move_many_cmd(
        file_path: Path = file_option,
        ids: str = typer.Option(
            ...,
            "--ids",
            help="Comma-separated resource ids to move.",
        ),
        new_parent: str = typer.Option(
            ...,
            "--new-parent",
            help="Destination parent id, or 'none' to move to root.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview diff and validation results without writing.",
        ),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Move many resources."""

        with guard:
            parsed_ids = [item.strip() for item in ids.split(",") if item.strip()]
            args = validate_payload(
                MoveManyArgs,
                {"ids": parsed_ids, "new_parent": new_parent},
            )

            def mutate(document: CommentedMap) -> bool:
                return move_many(document, ids=args.ids, new_parent_id=args.new_parent)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
