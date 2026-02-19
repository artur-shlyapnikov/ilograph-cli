"""CLI app wiring and registration."""

from __future__ import annotations

import typer
from rich.console import Console

from ilograph_cli.cli_support import CliGuard, MutationRunner, handle_error
from ilograph_cli.commands import alias as alias_commands
from ilograph_cli.commands import apply as apply_commands
from ilograph_cli.commands import batch as batch_commands
from ilograph_cli.commands import check as check_commands
from ilograph_cli.commands import context as context_commands
from ilograph_cli.commands import fmt as fmt_commands
from ilograph_cli.commands import group as group_commands
from ilograph_cli.commands import impact as impact_commands
from ilograph_cli.commands import move as move_commands
from ilograph_cli.commands import override as override_commands
from ilograph_cli.commands import perspective as perspective_commands
from ilograph_cli.commands import relation as relation_commands
from ilograph_cli.commands import rename as rename_commands
from ilograph_cli.commands import resolve as resolve_commands
from ilograph_cli.commands import resource as resource_commands
from ilograph_cli.commands import sequence as sequence_commands
from ilograph_cli.commands import walkthrough as walkthrough_commands
from ilograph_cli.core.errors import IlographCliError, ValidationError


def build_app(*, console: Console | None = None) -> typer.Typer:
    """Build Typer app with subcommands."""

    resolved_console = console or Console()
    guard = CliGuard(console=resolved_console)
    runner = MutationRunner(console=resolved_console)

    app = typer.Typer(
        help="Validate and safely mutate Ilograph YAML diagrams.",
        no_args_is_help=True,
    )
    rename_app = typer.Typer(
        help="Rename resources and resource IDs.",
        no_args_is_help=True,
    )
    move_app = typer.Typer(
        help="Move resource subtrees in the diagram.",
        no_args_is_help=True,
    )
    group_app = typer.Typer(
        help="Create groups and move many resources at once.",
        no_args_is_help=True,
    )
    relation_app = typer.Typer(
        help="Add, remove, and edit perspective relations.",
        no_args_is_help=True,
    )
    resource_app = typer.Typer(
        help="Create, delete, and clone resources.",
        no_args_is_help=True,
    )
    perspective_app = typer.Typer(
        help="Create, delete, rename, copy, and reorder perspectives.",
        no_args_is_help=True,
    )
    context_app = typer.Typer(
        help="Create, delete, rename, copy, and reorder contexts.",
        no_args_is_help=True,
    )
    alias_app = typer.Typer(
        help="Create, edit, delete, and list perspective aliases.",
        no_args_is_help=True,
    )
    override_app = typer.Typer(
        help="Create, edit, delete, and list perspective overrides.",
        no_args_is_help=True,
    )
    sequence_app = typer.Typer(
        help="Add, edit, remove, and list sequence steps.",
        no_args_is_help=True,
    )
    walkthrough_app = typer.Typer(
        help="Add, edit, remove, and list walkthrough slides.",
        no_args_is_help=True,
    )

    app.add_typer(rename_app, name="rename")
    app.add_typer(move_app, name="move")
    app.add_typer(group_app, name="group")
    app.add_typer(relation_app, name="relation")
    app.add_typer(resource_app, name="resource")
    app.add_typer(perspective_app, name="perspective")
    app.add_typer(context_app, name="context")
    app.add_typer(alias_app, name="alias")
    app.add_typer(override_app, name="override")
    app.add_typer(sequence_app, name="sequence")
    app.add_typer(walkthrough_app, name="walkthrough")

    check_commands.register(app, console=resolved_console, guard=guard)
    apply_commands.register(app, guard=guard, runner=runner)
    batch_commands.register(app, guard=guard, runner=runner)
    impact_commands.register(app, console=resolved_console, guard=guard)
    resolve_commands.register(app, console=resolved_console, guard=guard)
    fmt_commands.register(app, console=resolved_console, guard=guard)

    rename_commands.register(rename_app, guard=guard, runner=runner)
    move_commands.register(move_app, guard=guard, runner=runner)
    group_commands.register(group_app, guard=guard, runner=runner)
    relation_commands.register(
        relation_app,
        console=resolved_console,
        guard=guard,
        runner=runner,
    )
    resource_commands.register(resource_app, guard=guard, runner=runner)
    perspective_commands.register(
        perspective_app,
        console=resolved_console,
        guard=guard,
        runner=runner,
    )
    context_commands.register(
        context_app,
        console=resolved_console,
        guard=guard,
        runner=runner,
    )
    alias_commands.register(
        alias_app,
        console=resolved_console,
        guard=guard,
        runner=runner,
    )
    override_commands.register(
        override_app,
        console=resolved_console,
        guard=guard,
        runner=runner,
    )
    sequence_commands.register(
        sequence_app,
        console=resolved_console,
        guard=guard,
        runner=runner,
    )
    walkthrough_commands.register(
        walkthrough_app,
        console=resolved_console,
        guard=guard,
        runner=runner,
    )

    @app.callback()
    def main_callback() -> None:
        """Typer callback placeholder."""

    return app


_default_console = Console()
app = build_app(console=_default_console)


def main() -> None:
    """Console entrypoint."""

    try:
        app()
    except (ValidationError, IlographCliError) as exc:
        handle_error(_default_console, exc)
