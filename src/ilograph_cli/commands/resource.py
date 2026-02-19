"""`resource` command registration."""

from __future__ import annotations

from pathlib import Path

import typer
from ruamel.yaml.comments import CommentedMap

from ilograph_cli.cli_options import diff_mode_option, file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.core.arg_models import ResourceCloneArgs, ResourceCreateArgs, ResourceDeleteArgs
from ilograph_cli.ops.resource_ops import clone_resource, create_resource, delete_resource


def register(app: typer.Typer, *, guard: CliGuard, runner: MutationRunner) -> None:
    """Register resource subcommands."""

    @app.command("create")
    def resource_create_cmd(
        file_path: Path = file_option,
        resource_id: str = typer.Option(..., "--id"),
        name: str = typer.Option(..., "--name"),
        parent: str = typer.Option(
            "none",
            "--parent",
            help="Parent explicit id, or `none` for root.",
        ),
        subtitle: str | None = typer.Option(None, "--subtitle"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Create resource under parent or root."""

        with guard:
            args = validate_payload(
                ResourceCreateArgs,
                {
                    "id": resource_id,
                    "name": name,
                    "parent": parent,
                    "subtitle": subtitle,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return create_resource(
                    document,
                    resource_id=args.id,
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

    @app.command("delete")
    def resource_delete_cmd(
        file_path: Path = file_option,
        resource_id: str = typer.Option(..., "--id"),
        delete_subtree: bool = typer.Option(
            False,
            "--delete-subtree",
            help="Allow deleting resource that has children.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Delete resource by explicit id."""

        with guard:
            args = validate_payload(
                ResourceDeleteArgs,
                {
                    "id": resource_id,
                    "delete_subtree": delete_subtree,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return delete_resource(
                    document,
                    resource_id=args.id,
                    delete_subtree=args.delete_subtree,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("clone")
    def resource_clone_cmd(
        file_path: Path = file_option,
        resource_id: str = typer.Option(..., "--id"),
        new_id: str = typer.Option(..., "--new-id"),
        new_parent: str | None = typer.Option(
            None,
            "--new-parent",
            help="Explicit parent id. Omit to keep source parent, or pass `none` for root.",
        ),
        new_name: str | None = typer.Option(None, "--new-name"),
        with_children: bool = typer.Option(
            False,
            "--with-children/--shallow",
            help="Clone full subtree or only the resource node (default: shallow).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Clone resource to a new explicit id."""

        with guard:
            args = validate_payload(
                ResourceCloneArgs,
                {
                    "id": resource_id,
                    "new_id": new_id,
                    "new_parent": new_parent,
                    "new_name": new_name,
                    "with_children": with_children,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return clone_resource(
                    document,
                    resource_id=args.id,
                    new_id=args.new_id,
                    new_parent_id=args.new_parent,
                    new_name=args.new_name,
                    with_children=args.with_children,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
