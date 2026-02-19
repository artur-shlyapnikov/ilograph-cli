# Error cookbook

Fast map: error -> likely cause -> fix.

## Validation / identity

`resource not found: <id>`
- Cause: missing id/name in resource tree.
- Fix: check exact identifier (`id` first, fallback `name`), run `ilograph check`.

`resource id not unique: <id> (...)`
- Cause: duplicate resource id/name.
- Fix: make identifier unique; prefer explicit `id`.

`perspective not found: <id>`
- Cause: bad perspective id/name.
- Fix: verify perspective `id`/`name`.

`perspective id not unique: <id> (...)`
- Cause: duplicate perspective id/name.
- Fix: set unique `id` on perspectives.

`target id already exists: <id>`
- Cause: `rename.resource-id` target collides.
- Fix: choose unused `to` value.

`resource id already exists: <id>`
- Cause: `group.create` with existing id.
- Fix: choose unique `id`.

## Reference / relation

`broken-reference ... unknown reference '<token>'`
- Cause: relation/override/alias/walkthrough/sequence references unknown token.
- Fix: create resource, fix typo, or add perspective alias.

`relation must define from or to`
- Cause: add/edit removed both sides.
- Fix: set at least one of `from`/`to`.

`relation index out of range: <n>`
- Cause: wrong 1-based index.
- Fix: inspect perspective relations; use valid index.

`perspective has no relations: <perspective>`
- Cause: remove/edit requested on empty relation list.
- Fix: add relation first or target correct perspective.

## Bulk/template ops

`template contains '{context}' but target.contexts is not set`
- Cause: templated value used without `target.contexts`.
- Fix: add `target.contexts: [..]`.

`unknown context(s): ...`
- Cause: context name absent in document.
- Fix: align with `contexts[].name`.

`no relations matched for relation.remove-match`
- Cause: matcher found nothing with `requireMatch: true`.
- Fix: adjust `match`/`target` or set `requireMatch: false`.

`no relations matched for relation.edit-match`
- Cause: matcher found nothing with `requireMatch: true`.
- Fix: adjust `match`/`target` or set `requireMatch: false`.

```text
edit-match requires `set` or non-empty `clear`
```
- Cause: edit-match has neither payload nor clear fields.
- Fix: define at least one of `set` or `clear`.

`clear has duplicates`
- Cause: repeated field in `clear` array.
- Fix: dedupe clear list.

`invalid clear field(s): ...`
- Cause: unsupported field name in `clear`.
- Fix: use allowed fields only.

## YAML parse

`yaml parse error: ... found undefined alias ...`
- Cause: bracket reference parsed as YAML alias.
- Fix: quote bracket refs, example:

```yaml
from: "[*.cloudfront.net]"
```

## Debug flow

1. `ilograph check --file diagram.yaml`
2. `ilograph apply --file diagram.yaml --ops ops.yaml --dry-run`
3. `ilograph impact --file diagram.yaml --resource-id <id>`
4. `ilograph resolve --file diagram.yaml --ref "<expr>" --perspective <p>`
