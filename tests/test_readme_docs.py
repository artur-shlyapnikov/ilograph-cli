from __future__ import annotations

import shlex
from pathlib import Path

from typer.testing import CliRunner

from ilograph_cli.cli import app

runner = CliRunner()


def _extract_readme_command_paths(readme: str) -> list[list[str]]:
    paths: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    for raw_line in readme.splitlines():
        line = raw_line.strip()
        if not line.startswith("ilograph "):
            continue

        tokens = shlex.split(line)
        if not tokens or tokens[0] != "ilograph":
            continue

        command_path: list[str] = []
        for token in tokens[1:]:
            if token.startswith("-"):
                break
            command_path.append(token)

        if not command_path:
            continue

        signature = tuple(command_path)
        if signature in seen:
            continue

        seen.add(signature)
        paths.append(command_path)

    return paths


def test_readme_commands_exist_in_cli_help() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    command_paths = _extract_readme_command_paths(readme)

    assert command_paths, "README has no ilograph command examples"

    errors: list[str] = []
    for command_path in command_paths:
        result = runner.invoke(app, [*command_path, "--help"])
        if result.exit_code != 0:
            joined = " ".join(command_path)
            errors.append(f"`{joined}` -> exit={result.exit_code}; output={result.output!r}")

    assert not errors, "README command drift:\n" + "\n".join(errors)
