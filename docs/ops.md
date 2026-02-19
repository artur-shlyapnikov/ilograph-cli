# ops.yaml mini-spec

Root schema:

```yaml
ops:
  - op: <operation-name>
    ...
```

Rules:
- `ops` required, non-empty.
- Unknown keys rejected (`extra=forbid`).
- `apply` is transactional: any op error => nothing written.

## Operations

### `resource.create`

```yaml
- op: resource.create
  id: api
  name: API
  parent: platform # optional, default: none
  subtitle: Optional subtitle
```

Required:
- `id`
- `name`

Optional:
- `parent`
- `subtitle`

### `resource.delete`

```yaml
- op: resource.delete
  id: api
  deleteSubtree: true
```

Required:
- `id`

Optional:
- `deleteSubtree` (default `false`)

### `resource.clone`

```yaml
- op: resource.clone
  id: api
  newId: api_v2
  newParent: platform # optional
  newName: API v2 # optional
  withChildren: false # optional
```

Required:
- `id`
- `newId`

Optional:
- `newParent`
- `newName`
- `withChildren`

### `rename.resource`

```yaml
- op: rename.resource
  id: api
  name: API Gateway
```

Required:
- `id`
- `name`

### `rename.resource-id`

```yaml
- op: rename.resource-id
  from: api
  to: edge_api
```

Required:
- `from`
- `to`

Notes:
- `to` must be valid resource id.
- rewrites references across perspectives/contexts.

### `move.resource`

```yaml
- op: move.resource
  id: svc
  newParent: platform
  inheritStyleFromParent: true # optional
```

Required:
- `id`
- `newParent` (or `new_parent`)

Optional:
- `inheritStyleFromParent` (or `inherit_style_from_parent`, default `false`)

### `group.create`

```yaml
- op: group.create
  id: domain
  name: Domain
  parent: platform
  subtitle: Optional subtitle
```

Required:
- `id`
- `name`
- `parent`

Optional:
- `subtitle`

### `group.move-many`

```yaml
- op: group.move-many
  ids: [svc_a, svc_b]
  newParent: domain
```

Required:
- `ids` (non-empty list, no duplicates)
- `newParent` (or `new_parent`)

### `relation.add`

```yaml
- op: relation.add
  perspective: Runtime
  from: web
  to: api
  label: calls
```

Required:
- `perspective`
- at least one of `from` or `to`

Optional:
- `via`
- `label`
- `description`
- `arrowDirection` (`forward|backward|bidirectional`)
- `color`
- `secondary`

### `relation.remove`

```yaml
- op: relation.remove
  perspective: Runtime
  index: 2
```

Required:
- `perspective`
- `index` (`>= 1`, 1-based)

### `relation.edit`

```yaml
- op: relation.edit
  perspective: Runtime
  index: 2
  label: calls-v2
  clearDescription: true
```

Required:
- `perspective`
- `index` (`>= 1`, 1-based)

Optional set-fields:
- `from`, `to`, `via`, `label`, `description`
- `arrowDirection`, `color`, `secondary`

Optional clear-fields:
- `clearFrom`, `clearTo`, `clearVia`, `clearLabel`, `clearDescription`

Safety:
- relation must still define `from` or `to` after edit.

### `relation.add-many`

```yaml
- op: relation.add-many
  target:
    perspectives: [Runtime, Batch] # or "*"
    contexts: [prod, stage]
  from: app
  to: db_{context}
```

Required:
- `target`
- at least one of `from` or `to`

`target`:
- `perspectives`: list or `"*"` (default `"*"`)
- `contexts`: optional list

Template rule:
- if any field contains `{context}`, `target.contexts` must be set.

### `relation.remove-match`

```yaml
- op: relation.remove-match
  target:
    perspectives: [Runtime]
    contexts: [prod]
  match:
    from: app
    to: db_{context}
  requireMatch: true
```

Required:
- `target`
- `match` (at least one match field)

Optional:
- `requireMatch` (default `true`)

Match fields allowed:
- `from`, `to`, `via`, `label`, `description`, `arrowDirection`, `color`, `secondary`

### `relation.edit-match`

```yaml
- op: relation.edit-match
  target:
    perspectives: "*"
    contexts: [prod, stage]
  match:
    from: app
    to: db_{context}
  set:
    label: query-{context}
  clear: [description]
  requireMatch: true
```

Required:
- `target`
- `match` (at least one match field)
- at least one of:
  - `set` (non-empty)
  - `clear` (non-empty)

Optional:
- `requireMatch` (default `true`)

`clear` allowed values:
- `from`, `to`, `via`, `label`, `description`, `arrowDirection`, `color`, `secondary`

Validation:
- no duplicates in `clear`.
- resulting relation must keep `from` or `to`.

### `fmt.stable`

```yaml
- op: fmt.stable
```

No fields.

## Template/context behavior

`{context}` replacement:
- applies to string fields only.
- one rendered payload per context.
- duplicate rendered payloads deduplicated.

Context validation:
- all `target.contexts` must exist in document contexts.
- unknown context => error.

## Quick failure modes

- `ops must contain at least one operation`
- `template contains '{context}' but target.contexts is not set`
- `unknown context(s): ...`
- `no relations matched for relation.remove-match`
- `no relations matched for relation.edit-match`
