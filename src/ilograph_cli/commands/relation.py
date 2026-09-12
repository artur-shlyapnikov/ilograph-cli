"""`relation` command registration."""

from __future__ import annotations

import typer
from rich.console import Console

from ilograph_cli.cli_support import CliGuard, MutationRunner
from ilograph_cli.commands import relation_list as relation_list_commands
from ilograph_cli.commands import relation_mutate as relation_mutate_commands


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register relation subcommands."""

    relation_list_commands.register(app, console=console, guard=guard)
    relation_mutate_commands.register(app, guard=guard, runner=runner)
