# ilograph-cli

ilograph-cli validates and edits Ilograph YAML diagrams from a terminal. It
keeps comments and formatting where the YAML writer can preserve them. Write
commands validate the resulting document before replacing the input file.

## Requirements

- Python 3.12 or newer
- uv, or pip

## Install

The repository workflow uses uv:

```bash
uv sync
uv run ilograph --help
```

For an editable pip install:

```bash
python -m pip install -e '.[dev]'
ilograph --help
```

If you use the uv environment, prefix the commands below with `uv run`.

## Quickstart

Use an existing diagram YAML file. The commands below show the main read and
write paths:

```bash
ilograph check --file diagram.yaml --mode ilograph-native
ilograph check --file diagram.yaml --mode strict --json

ilograph impact --file diagram.yaml --resource-id api
ilograph resolve --file diagram.yaml --ref "app,db" --perspective Runtime
ilograph relation list --file diagram.yaml --perspective Runtime --json

ilograph apply --file diagram.yaml --ops ops.yaml --dry-run --diff full
ilograph batch --file diagram.yaml --op '{"op":"rename.resource","id":"api","name":"API v2"}'
ilograph rename resource --file diagram.yaml --id api --name "API Gateway"
```

`check`, `impact`, `resolve`, `find`, and list commands read the diagram. The
other examples change the file unless they include `--dry-run`.

## Command reference

### Validation and inspection

`check` parses and validates the document. The default mode is
`ilograph-native`; `strict` applies the stricter validation set. Use `--json`
for machine-readable output. `--ignore-rule` and `--only-rule` accept repeated
flags or comma-separated rule names.

`impact` lists the places where a resource is used. `resolve` and `find` show
how reference tokens resolve in a perspective. They support `--json` and
`--no-truncate`.

Each collection has `list` and `ls` aliases where implemented:

| Collection | Example |
| --- | --- |
| Relations | `ilograph relation list --file diagram.yaml --perspective Runtime` |
| Perspectives | `ilograph perspective list --file diagram.yaml` |
| Contexts | `ilograph context list --file diagram.yaml` |
| Aliases | `ilograph alias list --file diagram.yaml --perspective Runtime` |
| Overrides | `ilograph override list --file diagram.yaml --perspective Runtime` |
| Sequences | `ilograph sequence list --file diagram.yaml --perspective Flow` |
| Walkthroughs | `ilograph walkthrough list --file diagram.yaml --perspective Flow` |

The stable formatter currently parses the file and reports that no changes
were made:

```bash
ilograph fmt --file diagram.yaml --stable
ilograph fmt --file diagram.yaml --stable --dry-run
```

### Write commands

The write commands support `--dry-run` and a `--diff` mode:

| Option | Result |
| --- | --- |
| `--dry-run` | Show validation and diff output without writing. |
| `--diff summary` | Show a short diff preview. This is the default. |
| `--diff full` | Show the complete unified diff. |
| `--diff none` | Show counts and touched sections without patch text. |

The runner reads the file, applies operations in memory, validates the
resulting document in strict mode, and writes it atomically. If validation
fails, the runner leaves the input file unchanged. `apply` and `batch` run all operations
as one transaction.

Common operations:

```bash
ilograph rename resource --file diagram.yaml --id api --name "API Gateway"
ilograph rename resource-id --file diagram.yaml --from api --to edge_api
ilograph move resource --file diagram.yaml --id service --new-parent platform

ilograph group create --file diagram.yaml --id domain --name Domain --parent platform
ilograph group move-many --file diagram.yaml --ids svc_a,svc_b --new-parent domain

ilograph resource create --file diagram.yaml --id edge --name Edge --parent platform
ilograph resource clone --file diagram.yaml --id edge --new-id edge_copy --shallow
ilograph resource delete --file diagram.yaml --id edge_copy

ilograph relation add --file diagram.yaml --perspective Runtime --from web --to api --label calls
ilograph relation edit --file diagram.yaml --perspective Runtime --index 1 --label "calls v2"
ilograph relation remove --file diagram.yaml --perspective Runtime --index 1

ilograph perspective create --file diagram.yaml --id Batch --name Batch --extends Runtime
ilograph context create --file diagram.yaml --name stage --extends prod
```

The `batch` command accepts repeated JSON objects:

```bash
ilograph batch --file diagram.yaml --op '{"op":"rename.resource","id":"api","name":"API v2"}' --op '{"op":"relation.add","perspective":"Runtime","from":"web","to":"api"}' --dry-run --diff full
```

`apply` reads the same operation format from an `ops.yaml` file:

```yaml
ops:
  - op: relation.add
    perspective: Runtime
    from: web
    to: api
    label: calls
  - op: rename.resource
    id: api
    name: API v2
```

Run it with:

```bash
ilograph apply --file diagram.yaml --ops ops.yaml --dry-run --diff full
```

The complete operation schema is in [`docs/ops.md`](docs/ops.md).

## Errors

The CLI reports validation and operation errors before writing. Common causes
include an unknown resource, a duplicate identifier, a missing perspective,
an invalid one-based relation index, or a reference to an unknown token.

Use this sequence to inspect a failed change:

```bash
ilograph check --file diagram.yaml
ilograph apply --file diagram.yaml --ops ops.yaml --dry-run --diff full
ilograph impact --file diagram.yaml --resource-id api
ilograph resolve --file diagram.yaml --ref "api" --perspective Runtime
```

See [`docs/errors.md`](docs/errors.md) for the full error list and fixes.

## Development

Install development dependencies and run the repository checks:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
uv run lint-imports --config .importlinter
```

The package entry point is `ilograph_cli.cli:main`. Tests live in `tests/`.
