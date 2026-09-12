"""`relation` list command registration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypedDict

import typer
from rich.console import Console
from rich.table import Table
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.cli_options import file_option
from ilograph_cli.cli_support import CliGuard
from ilograph_cli.commands.relation_shared import (
    _build_relation_template,
    _parse_multi_values,
    perspective_filter_option,
)
from ilograph_cli.core.index import build_perspective_locations, get_single_perspective
from ilograph_cli.core.relation_types import RelationTemplate
from ilograph_cli.io.yaml_io import load_document


class RelationRow(TypedDict):
    perspective: str
    index: int
    from_: str | None
    to: str | None
    via: str | None
    label: str | None
    description: str | None
    arrow_direction: str | None
    color: str | None
    secondary: bool


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
) -> None:
    """Register relation list subcommands."""

    @app.command("ls")
    @app.command("list")
    def relation_list_cmd(
        file_path: Path = file_option,
        perspective: list[str] | None = perspective_filter_option,
        from_ref: str | None = typer.Option(None, "--from"),
        to_ref: str | None = typer.Option(None, "--to"),
        via: str | None = typer.Option(None, "--via"),
        label: str | None = typer.Option(None, "--label"),
        description: str | None = typer.Option(None, "--description"),
        arrow_direction: str | None = typer.Option(None, "--arrow-direction"),
        color: str | None = typer.Option(None, "--color"),
        secondary: bool | None = typer.Option(
            None,
            "--secondary/--no-secondary",
            help="Filter by relation.secondary",
        ),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap/truncate table columns",
        ),
    ) -> None:
        """List perspective relations with filters."""

        with guard:
            document = load_document(file_path)
            selected_perspectives = _resolve_perspectives(
                document,
                _parse_multi_values(perspective),
            )
            filters = _build_relation_template(
                from_ref=from_ref,
                to_ref=to_ref,
                via=via,
                label=label,
                description=description,
                arrow_direction=arrow_direction,
                color=color,
                secondary=secondary,
            )
            rows = _list_relations(document, selected_perspectives, filters=filters)

            if json_output:
                payload = {
                    "count": len(rows),
                    "filters": filters,
                    "rows": rows,
                }
                typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
                return

            if not rows:
                console.print("no relations found")
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title="Relations")
            table.add_column("Perspective", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Index", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("From", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("To", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Via", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Label", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Direction", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Secondary", overflow=overflow_mode, no_wrap=no_truncate)

            for row in rows:
                from_value = row["from_"] or "-"
                to_value = row["to"] or "-"
                via_value = row["via"] or "-"
                label_value = row["label"] or "-"
                direction_value = row["arrow_direction"] or "-"
                table.add_row(
                    row["perspective"],
                    str(row["index"]),
                    from_value,
                    to_value,
                    via_value,
                    label_value,
                    direction_value,
                    str(row["secondary"]),
                )
            console.print(table)
            console.print(f"total: {len(rows)}")


def _list_relations(
    document: CommentedMap,
    selected_perspectives: list[str],
    *,
    filters: RelationTemplate,
) -> list[RelationRow]:
    rows: list[RelationRow] = []
    for perspective_id in selected_perspectives:
        perspective = get_single_perspective(document, perspective_id)
        relations = perspective.node.get("relations")
        if not isinstance(relations, CommentedSeq):
            continue

        for index, relation in enumerate(relations, start=1):
            if not isinstance(relation, CommentedMap):
                continue
            if not _relation_matches_filters(relation, filters):
                continue

            secondary = relation.get("secondary")
            rows.append(
                {
                    "perspective": perspective.identifier,
                    "index": index,
                    "from_": _as_optional_str(relation.get("from")),
                    "to": _as_optional_str(relation.get("to")),
                    "via": _as_optional_str(relation.get("via")),
                    "label": _as_optional_str(relation.get("label")),
                    "description": _as_optional_str(relation.get("description")),
                    "arrow_direction": _as_optional_str(relation.get("arrowDirection")),
                    "color": _as_optional_str(relation.get("color")),
                    "secondary": bool(secondary) if isinstance(secondary, bool) else False,
                }
            )
    return rows


def _relation_matches_filters(relation: CommentedMap, filters: RelationTemplate) -> bool:
    for key, expected in filters.items():
        if key == "secondary":
            actual = relation.get("secondary")
            actual_bool = actual if isinstance(actual, bool) else False
            if actual_bool != expected:
                return False
            continue
        if relation.get(key) != expected:
            return False
    return True


def _resolve_perspectives(document: CommentedMap, selected: list[str]) -> list[str]:
    if selected:
        return [get_single_perspective(document, item).identifier for item in selected]
    return [item.identifier for item in build_perspective_locations(document)]


def _as_optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None
