# Design Notes

## B2 — idempotency key

The idempotency key is the **SHA-256 of the canonical JSON (keys sorted, no whitespace) of the
plan's `resource_changes` list**. `cost_tag_check.py` prints it on every run as
`plan fingerprint (idempotency key): <hash>`.

The check is idempotent because it is a pure function of that key: the same `resource_changes`
produce the same fingerprint, and the report and exit code are derived only from that content. It
reads the plan, writes nothing, and keeps no state, so a second run on an unchanged plan prints the
same fingerprint, the same sorted list of offending addresses, and the same exit code. There is no
cache or log to append to, so duplicates cannot arise. Offending addresses are collected in a `set`
and sorted, so the output does not depend on input order. If the plan changes, the fingerprint
changes, which makes it easy to see in CI logs that two runs checked different plans.

## Any other decision with a non-obvious alternative

- **Tag key: `landlord_account_id`, not `tenant_id`.** The README says `LandlordAccount` is the
  billing unit and that the current tagging reflects how things were built, not a spec. A resource
  carrying only `tenant_id` fails the check (`listing_media` in the fixture does exactly this).
  Alternative considered: accept either tag. Rejected, because `tenant_id` rolls up to many
  tenants per account and cannot be billed against.
- **Stateless check vs. recording checked plans.** Alternative: store fingerprints in a file and
  skip plans "already checked". Rejected: it adds state that can go stale and could turn a failing
  plan into a silent pass on a rerun. Statelessness gives idempotency with nothing to corrupt.
- **Generic taggable detection.** A resource is checked if its planned `after` has a `tags` or
  `tags_all` attribute, instead of a hardcoded list of resource types. New resource types are
  covered automatically; resources with no tag support (no such attribute) are not falsely failed.
- **`tags_all` is honored.** The AWS provider's `default_tags` show up in `tags_all`, not `tags`.
  Merging both (explicit tags win) avoids false failures when the tag is applied provider-wide.
- **Empty values fail.** `landlord_account_id: ""` is treated as missing, since it can't be billed.
- **Actions checked: `create` and `update`.** A replace is `["delete","create"]` and is covered by
  `create`. `delete`, `no-op` and `read` are skipped, since their `after` is null or unchanged.
- **Access check follows the hierarchy.** Report -> tenant -> property -> `landlord_account_id`,
  compared with the manager's account. Alternative: denormalize the account ID onto reports. Rejected:
  seed data must not change, and a duplicated field can drift from the real ownership chain. The
  function fails closed on any missing link (tenant, property, or an empty account ID on either
  side), so an empty-string match can never grant access.
- **Pure core for testing.** `check_plan_data(plan_dict)` holds the logic and `check_plan(path)` is a
  thin file/print wrapper, so tests use in-memory dicts and only the happy-path tests touch the file.
