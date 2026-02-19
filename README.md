# ilograph-cli

CLI for safe Ilograph YAML edits.
Goal: minimal diffs, transactional writes, predictable failures.

## Requirements

- Python 3.12+
- `uv` (recommended) or `pip`

## Install

Preferred (repo workflow):

```bash
uv sync --dev
uv run ilograph --help
```

Alternative:

```bash
python -m pip install -e '.[dev]'
ilograph --help
```

Examples below use installed `ilograph`.
Repo-only flow: prefix commands with `uv run` (for example `uv run ilograph check ...`).

## Architecture checks

Rules live in `.importlinter` + `ruff` (`TID`).

```bash
uv run lint-imports --config .importlinter
uv run ruff check .
```

## Quickstart

```bash
ilograph check --file diagram.yaml --mode ilograph-native
ilograph check --file diagram.yaml --mode strict --json

ilograph apply --file diagram.yaml --ops ops.yaml --dry-run --diff summary
ilograph apply --file diagram.yaml --ops ops.yaml --diff full
ilograph batch --file diagram.yaml --op '{"op":"rename.resource","id":"api","name":"API v2"}' --op '{"op":"relation.add","perspective":"Runtime","from":"web","to":"api"}'

ilograph impact --file diagram.yaml --resource-id api
ilograph impact --file diagram.yaml --resource-id api --json

ilograph resolve --file diagram.yaml --ref "app,db,unknown" --perspective Runtime
ilograph find --file diagram.yaml --ref "app,db" --perspective Runtime

ilograph relation list --file diagram.yaml --perspective Runtime --json
ilograph perspective ls --file diagram.yaml
ilograph context ls --file diagram.yaml --json

ilograph fmt --file diagram.yaml --stable
```

## CRUD command examples

```bash
ilograph rename resource --file diagram.yaml --id api --name "API Gateway"
ilograph rename resource-id --file diagram.yaml --from api --to edge_api

ilograph move resource --file diagram.yaml --id svc --new-parent platform
ilograph move resource --file diagram.yaml --id svc --new-parent platform --inherit-style-from-parent

ilograph group create --file diagram.yaml --id domain --name "Domain" --parent platform
ilograph group move-many --file diagram.yaml --ids svc1,svc2 --new-parent domain

ilograph relation add --file diagram.yaml --perspective Runtime --from web --to api --label calls
ilograph relation edit --file diagram.yaml --perspective Runtime --index 2 --label "calls-v2"
ilograph relation remove --file diagram.yaml --perspective Runtime --index 3
ilograph relation ls --file diagram.yaml --perspective Runtime
ilograph relation edit-match --file diagram.yaml --perspective Runtime --match-from web --set-label calls-v3
ilograph relation remove-match --file diagram.yaml --perspective Runtime --from web --to api

ilograph resource create --file diagram.yaml --id edge --name Edge --parent platform
ilograph resource clone --file diagram.yaml --id edge --new-id edge_copy --shallow
ilograph resource delete --file diagram.yaml --id edge_copy

ilograph perspective create --file diagram.yaml --id Batch --name Batch --extends Runtime
ilograph perspective copy --file diagram.yaml --id Runtime --new-id Runtime_copy
ilograph perspective rename --file diagram.yaml --id Runtime_copy --new-id Runtime_shadow
ilograph perspective reorder --file diagram.yaml --id Batch --index 1
ilograph perspective delete --file diagram.yaml --id Runtime_shadow
ilograph perspective list --file diagram.yaml

ilograph context create --file diagram.yaml --name stage --extends prod
ilograph context copy --file diagram.yaml --name prod --new-name prod_copy
ilograph context rename --file diagram.yaml --name prod_copy --new-name prod_shadow
ilograph context reorder --file diagram.yaml --name stage --index 1
ilograph context delete --file diagram.yaml --name prod_shadow
ilograph context list --file diagram.yaml --json

ilograph alias add --file diagram.yaml --perspective Runtime --alias backend --for api,db
ilograph alias edit --file diagram.yaml --perspective Runtime --alias backend --new-alias data
ilograph alias remove --file diagram.yaml --perspective Runtime --alias data
ilograph alias ls --file diagram.yaml --perspective Runtime

ilograph override add --file diagram.yaml --perspective Runtime --resource-id db --parent-id app --scale 0.8
ilograph override edit --file diagram.yaml --perspective Runtime --resource-id db --clear-parent-id --scale 0.6
ilograph override remove --file diagram.yaml --perspective Runtime --resource-id db
ilograph override ls --file diagram.yaml --perspective Runtime

ilograph sequence add --file diagram.yaml --perspective Flow --start app --to api --label "call"
ilograph sequence edit --file diagram.yaml --perspective Flow --index 1 --to-and-back app
ilograph sequence remove --file diagram.yaml --perspective Flow --index 1
ilograph sequence ls --file diagram.yaml --perspective Flow

ilograph walkthrough add --file diagram.yaml --perspective Flow --text "Step 1" --select app
ilograph walkthrough edit --file diagram.yaml --perspective Flow --index 1 --highlight api
ilograph walkthrough remove --file diagram.yaml --perspective Flow --index 1
ilograph walkthrough ls --file diagram.yaml --perspective Flow
```

## Command matrix

| Command | Purpose | Mutates | `--dry-run` | Notes |
| --- | --- | --- | --- | --- |
| `check` | Validate structure/references | no | n/a | `--mode strict|ilograph-native`, `--json`, rule filters |
| `impact` | Show resource usage sites | no | n/a | `--json`, `--no-truncate` |
| `resolve` / `find` | Explain reference token resolution | no | n/a | `--perspective`, `--json`, `--no-truncate` |
| `fmt --stable` | Round-trip parse/emit safety pass | no | yes | only `--stable` supported |
| `apply --ops` | Run `ops.yaml` transaction | yes | yes | file unchanged on any op failure |
| `rename resource` | Rename display name | yes | yes | command validates before write |
| `rename resource-id` | Rename identifier + rewrite refs | yes | yes | command validates before write |
| `move resource` | Move resource subtree | yes | yes | command validates before write |
| `group create` | Create group resource | yes | yes | command validates before write |
| `group move-many` | Move many resources | yes | yes | command validates before write |
| `relation add` | Append relation row | yes | yes | command validates before write |
| `relation edit` | Edit relation by 1-based index | yes | yes | command validates before write |
| `relation remove` | Remove relation by 1-based index | yes | yes | command validates before write |
| `relation ls/list` | List relations with filters | no | n/a | `--json`, `--perspective`, field filters |
| `relation edit-match` | Bulk edit matched relations | yes | yes | matcher + set/clear without row index |
| `relation remove-match` | Bulk remove matched relations | yes | yes | matcher + `--allow-noop` support |
| `resource create` | Create resource under parent/root | yes | yes | `--parent none` puts resource at root |
| `resource clone` | Clone resource to new id | yes | yes | `--shallow` default; `--with-children` guarded |
| `resource delete` | Delete resource by explicit id | yes | yes | blocks subtree delete unless `--delete-subtree` |
| `perspective ls/list` | List perspectives | no | n/a | `--json` |
| `perspective create/rename/delete/reorder/copy` | Perspective lifecycle | yes | yes | handles `extends` references safely |
| `context ls/list` | List contexts | no | n/a | `--json` |
| `context create/rename/delete/reorder/copy` | Context lifecycle | yes | yes | handles `extends` references safely |
| `alias ls/add/edit/remove` | Perspective aliases CRUD | mix | mix | keyed by `--alias` (stable UX) |
| `override ls/add/edit/remove` | Perspective overrides CRUD | mix | mix | keyed by `--resource-id` |
| `sequence ls/add/edit/remove` | Sequence steps CRUD | mix | mix | supports sequence bootstrap via `--start` |
| `walkthrough ls/add/edit/remove` | Walkthrough slides CRUD | mix | mix | supports fine-grained clear flags |

For mutating commands with `--dry-run`, diff modes:
- `--diff summary` (default): preview + truncation for large patches.
- `--diff full`: full unified diff.
- `--diff none`: counts only, no patch text.

## `ops.yaml` examples

```yaml
ops:
  - op: relation.add-many
    target:
      perspectives: [Runtime, Batch] # or "*"
      contexts: [prod, stage]
    from: app
    to: db_{context}
    label: call-{context}

  - op: relation.edit-match
    target:
      perspectives: "*"
      contexts: [prod, stage]
    match:
      from: app
      to: db_{context}
      label: read-{context}
    set:
      label: query-{context}
      secondary: true

  - op: relation.remove-match
    target:
      perspectives: [Batch]
      contexts: [stage]
    match:
      from: app
      to: db_{context}
      label: query-{context}

  - op: fmt.stable
```

Ops mini-spec: [`docs/ops.md`](docs/ops.md)  
Errors + fixes: [`docs/errors.md`](docs/errors.md)
