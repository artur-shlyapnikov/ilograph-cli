# Check validation

Check parses and validates a diagram file and reports rule-coded issues without ever writing to the file.

## Sub-features

- `check-native` validates with the default ilograph-native rule set.
- `check-strict` applies the stricter validation set that also flags external references.
- `check-json` emits machine-readable output with a per-code summary.
- `check-filters` narrows validation with `--ignore-rule` and `--only-rule`.

## How to get to it (user POV)

- Run `ilograph check --file diagram.yaml` in a terminal.
- Run `ilograph check --file diagram.yaml --mode strict` for strict validation.
- Run `ilograph check --file diagram.yaml --mode strict --json` for machine-readable output.
- Run `ilograph check --file diagram.yaml --ignore-rule <code>` or `--only-rule <code>` to filter rules.

## Driving it with control-ilograph

Preconditions:

- `helpers/control-ilograph doctor` reports all checks passed.
- Work dir holds a copy of `tests/golden/rename_id/input.yaml` as `diagram.yaml` and a copy of `tests/invalid_check.yaml` as `invalid.yaml`.

- **Native pass.** Validate the golden fixture. Run `helpers/control-ilograph cli -- check --file "$D/diagram.yaml"`. Exit code `0` and stdout contains `check ok`.
- **Strict external reference.** Validate a diagram referencing an external token. Write `strict.yaml` with a `Runtime` relation `to: Ext::ImportedResource` and run `helpers/control-ilograph cli -- check --file "$D/strict.yaml" --mode strict`. Exit code `1` and stdout contains `broken-reference` and `Ext::ImportedResource`; the same file with `--mode ilograph-native` exits `0`.
- **Invalid fixture.** Validate the known-bad file. Run `helpers/control-ilograph cli -- check --file "$D/invalid.yaml"`. Exit code `1` and stdout contains `duplicate-resource-id`, `broken-reference`, and `restricted-resource-id`.
- **JSON summary.** Re-run the invalid file. Run `helpers/control-ilograph cli -- check --file "$D/invalid.yaml" --json`. Exit code `1`; parse stdout as JSON and assert `ok` is `false` and `summary.by_code` counts `duplicate-resource-id` and `broken-reference` at `>= 1`.
- **Rule filters.** Re-run strict mode ignoring the failing rule. Run `helpers/control-ilograph cli -- check --file "$D/strict.yaml" --mode strict --ignore-rule broken-reference`. Exit code `0`. Then run with `--only-rule broken-reference` and require exit code `1`.
- **Proof.** Save each transcript to `$EVIDENCE/check.transcript.txt` and the JSON payload to `$EVIDENCE/check.json`. `check` never writes: `diff -u` the diagram against `before.yaml` is empty.

## Gotchas

- The default mode is `ilograph-native`, not `strict`. Omitting `--mode` hides `broken-reference` findings on external tokens.
- `--ignore-rule` and `--only-rule` accept repeats or comma-separated values; a typo in a rule name silently matches nothing.
- Exit code is the assertion: `0` means valid, `1` means issues found. Always capture it; output text alone is not proof.
- `tests/invalid_check.yaml` is a repo fixture, not a work file. Copy it into the work dir before driving.
