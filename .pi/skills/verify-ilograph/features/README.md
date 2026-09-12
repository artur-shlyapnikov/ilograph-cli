# ilograph CLI verification map

This directory is the maintained source for verifying the user-facing
behavior of the `ilograph` CLI. Read this index before driving the app,
then use the matching feature file as the recipe.

## Baseline preconditions

- Deps installed once with `uv sync` from the repo root.
- Each drive uses its own work dir under `/tmp/ilograph-verify-$RUN_ID/work/`
  with a fixture copy made via
  `helpers/control-ilograph fixture <src> <destdir> [name]`.
- The golden source fixtures live in `tests/golden/<name>/input.yaml`;
  `tests/golden/rename_id/input.yaml` is the default rich fixture (nested
  resources, anchors, aliases, relations, overrides, walkthrough,
  sequence, contexts).
- Run `helpers/control-ilograph doctor --file <diagram>` and require all
  checks passed before driving.
- Never drive a diagram outside the work dir. Never point two concurrent
  mutations at the same `--file`.

## Driving conventions

- Start every recipe from a fresh fixture copy unless its preconditions
  say otherwise.
- Save `before.yaml` before any mutation; `diff -u before.yaml
  diagram.yaml` after.
- Treat every command as literal. Keep quoted names, `--id` values, and
  `--op` JSON unchanged.
- Run app actions through `helpers/control-ilograph cli -- <args>`.
- Read commands (`check`, `impact`, `resolve`, `find`, `* list`) prove
  state; write commands must be followed by one read command proving the
  new state.
- Restore nothing: fixture copies are disposable. Retain proof artifacts
  during cleanup.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final
  screen: command line, stdout, stderr, exit code, plus the file diff.
- Read proof includes the command, stdout, stderr, and exit code.
- Mutation proof includes the diff and a read-only second view of the
  stored value (`check --mode strict`, `relation list --json`, `impact`).
- `--dry-run` proof includes a byte-identical `diff` against `before.yaml`.
- Record the feature ID and entry point used with every artifact.
- Report an unreachable path with the attempted command and the unmet
  precondition.
- Do not report a skipped entry point as verified through a different
  path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the
user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with control-ilograph` starts with `Preconditions:` and uses
   labeled bullets that pair each user action with an exact command and
   observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

Keep implementation details out of the map. Name only user paths, stable
handles, required state, commands, and observable proof.

## Features

- [Check validation](./check.md) covers native/strict modes, JSON output,
  and rule filters.
- [Safe refactors](./safe-refactor.md) covers rename, move, group, and
  resource lifecycle with dry-run and transactional safety.
- [Relation editing](./relations.md) covers add, edit, remove, match
  variants, and listing perspective relations.
- [Apply and batch transactions](./apply-batch.md) covers ops files,
  inline ops, atomicity, and schema errors.
- [Inspection and formatting](./inspect.md) covers impact, resolve/find,
  collection lists, and stable formatting.
