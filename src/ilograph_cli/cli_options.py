"""Shared Typer option definitions."""

from __future__ import annotations

import typer

file_option = typer.Option(
    ...,
    "--file",
    "-f",
    help="Path to the Ilograph diagram YAML file.",
    exists=True,
    readable=True,
    dir_okay=False,
    resolve_path=False,
)

ops_file_option = typer.Option(
    ...,
    "--ops",
    help="Path to ops YAML file (transaction payload).",
    exists=True,
    readable=True,
    dir_okay=False,
)

ignore_rule_option = typer.Option(
    None,
    "--ignore-rule",
    help="Ignore validation code(s). Repeat flag or pass comma-separated values.",
)

only_rule_option = typer.Option(
    None,
    "--only-rule",
    help="Keep only validation code(s). Repeat flag or pass comma-separated values.",
)

diff_mode_option = typer.Option(
    "summary",
    "--diff",
    help="Diff output mode: full | summary | none (default: summary).",
)
