"""
B2, part 2 — implement the cost-tagging check.

Read fixtures/plan.json for the shape of a `terraform show -json` plan: a `resource_changes`
list, where each entry has a `type`, an `address`, and `change.after.tags`.

Implement check_plan() so it:
  - Looks at every resource being created or changed (skip anything not in
    change.actions, e.g. a pure "no-op" / "read" change).
  - Fails (returns a non-zero exit code) if the resource is missing the tag that identifies
    the real billing unit, per README.md's domain model — not whatever tag the resource
    happens to already carry.
  - Is idempotent: running this twice against the same plan file produces the same result,
    with no duplicate output and no flipped pass/fail.
  - Prints which specific resource address(es) are missing the tag.

Run manually: python scripts/cost_tag_check.py fixtures/plan.json
"""
import hashlib
import json
import sys

BILLING_TAG = "landlord_account_id"
CHECKED_ACTIONS = {"create", "update"}  # a replace is ["delete", "create"], so it is covered


def _effective_tags(after: dict) -> dict:
    """Explicit tags plus provider default_tags (tags_all); either may be null in a plan."""
    return {**(after.get("tags_all") or {}), **(after.get("tags") or {})}


def _is_taggable(after: dict) -> bool:
    """A resource is taggable if its planned state has a tags/tags_all attribute at all."""
    return "tags" in after or "tags_all" in after


def plan_fingerprint(plan: dict) -> str:
    """
    The idempotency key: SHA-256 of the canonical JSON (sorted keys, no whitespace) of the
    plan's `resource_changes`. Same resource changes -> same key -> same report.
    """
    canonical = json.dumps(plan.get("resource_changes", []), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def find_untagged(plan: dict) -> list[str]:
    """Addresses of created/changed taggable resources lacking a non-empty billing tag, sorted."""
    missing = set()
    for rc in plan.get("resource_changes", []):
        change = rc.get("change") or {}
        if not CHECKED_ACTIONS & set(change.get("actions") or []):
            continue
        after = change.get("after")
        if not isinstance(after, dict) or not _is_taggable(after):
            continue
        if not _effective_tags(after).get(BILLING_TAG):
            missing.add(rc["address"])
    return sorted(missing)


def check_plan_data(plan: dict) -> tuple[int, str]:
    """Pure core: returns (exit_code, report). No I/O, no state, so reruns are identical."""
    missing = find_untagged(plan)
    lines = [f"plan fingerprint (idempotency key): {plan_fingerprint(plan)}"]
    if missing:
        lines.append(f"FAIL: {len(missing)} resource(s) missing '{BILLING_TAG}':")
        lines.extend(f"  - {address}" for address in missing)
        return 1, "\n".join(lines)
    lines.append(f"PASS: every taggable resource being created/changed has '{BILLING_TAG}'")
    return 0, "\n".join(lines)


def check_plan(plan_path: str) -> int:
    """
    Returns an exit code: 0 if every taggable resource being created/changed has
    `landlord_account_id`, non-zero otherwise.
    """
    with open(plan_path) as f:
        plan = json.load(f)
    code, report = check_plan_data(plan)
    print(report)
    return code


if __name__ == "__main__":
    sys.exit(check_plan(sys.argv[1]))
