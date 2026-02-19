"""`check` command registration."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from ilograph_cli.cli_options import file_option, ignore_rule_option, only_rule_option
from ilograph_cli.cli_support import CliGuard
from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.validators import ValidationIssue, ValidationMode, validate_document
from ilograph_cli.io.yaml_io import load_document


def register(app: typer.Typer, *, console: Console, guard: CliGuard) -> None:
    """Register `check` command."""

    @app.command("check")
    def check(
        file_path: Path = file_option,
        mode: str = typer.Option(
            "ilograph-native",
            "--mode",
            help=(
                "Validation mode: strict | ilograph-native "
                "(default: ilograph-native)."
            ),
        ),
        ignore_rule: list[str] | None = ignore_rule_option,
        only_rule: list[str] | None = only_rule_option,
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable JSON (includes summary and issue list).",
        ),
    ) -> None:
        """Parse + validate document."""

        with guard:
            normalized_mode = mode.strip().lower()
            if normalized_mode not in {"strict", "ilograph-native"}:
                raise ValidationError(
                    f"unknown mode: {mode} (expected: strict|ilograph-native)"
                )

            document = load_document(file_path)
            result = validate_document(document, mode=cast(ValidationMode, normalized_mode))

            ignore_rules = _normalize_rule_names(ignore_rule or [])
            only_rules = _normalize_rule_names(only_rule or [])
            issues = _filter_issues(
                result.issues,
                ignore_rules=ignore_rules,
                only_rules=only_rules,
            )
            ok = not issues

            if json_output:
                payload = {
                    "ok": ok,
                    "mode": normalized_mode,
                    "summary": {
                        "total": len(issues),
                        "by_code": _issues_summary(issues),
                    },
                    "issues": [
                        {
                            "code": issue.code,
                            "path": issue.path,
                            "message": issue.message,
                        }
                        for issue in issues
                    ],
                }
                typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
                if not ok:
                    raise typer.Exit(code=1)
                return

            if ok:
                console.print("check ok: 0 issues found")
                return

            table = Table(title=f"Validation issues ({len(issues)})")
            table.add_column("Code", overflow="fold")
            table.add_column("Path", overflow="fold")
            table.add_column("Message", overflow="fold")
            for issue in issues:
                table.add_row(issue.code, issue.path, issue.message)
            console.print(table)
            raise typer.Exit(code=1)


def _normalize_rule_names(raw: list[str]) -> set[str]:
    names: set[str] = set()
    for item in raw:
        for candidate in item.split(","):
            code = candidate.strip()
            if code:
                names.add(code)
    return names


def _filter_issues(
    issues: list[ValidationIssue],
    *,
    ignore_rules: set[str],
    only_rules: set[str],
) -> list[ValidationIssue]:
    filtered: list[ValidationIssue] = []
    for issue in issues:
        if only_rules and issue.code not in only_rules:
            continue
        if issue.code in ignore_rules:
            continue
        filtered.append(issue)
    return filtered


def _issues_summary(issues: list[ValidationIssue]) -> dict[str, int]:
    counter = Counter(issue.code for issue in issues)
    return dict(sorted(counter.items()))
