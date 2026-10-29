"""
Write tests here proving:
  1. Happy path: running the check against fixtures/plan.json correctly flags the resources
     missing `landlord_account_id` (listing_media, mls_feed_sync) and passes the ones that
     have it (landlord_media[0], screening_report_export).
  2. Idempotency: running the check twice against the same plan file produces the same
     result both times, with no duplicated output.

Use a test double / your own in-memory plan dict where you don't need a real file on disk —
you don't need to shell out to the real script for every case.
"""
from pathlib import Path

from scripts.cost_tag_check import (
    check_plan,
    check_plan_data,
    find_untagged,
    plan_fingerprint,
)

FIXTURE = str(Path(__file__).resolve().parent.parent / "fixtures" / "plan.json")


def _rc(address, actions, after):
    return {"address": address, "type": "x", "change": {"actions": actions, "after": after}}


def test_fixture_flags_resources_missing_billing_tag(capsys):
    assert check_plan(FIXTURE) == 1
    out = capsys.readouterr().out
    assert "aws_s3_bucket.listing_media" in out  # has tenant_id only
    assert "aws_lambda_function.mls_feed_sync" in out  # empty tags
    assert "landlord_media[0]" not in out
    assert "screening_report_export" not in out


def test_tenant_id_alone_is_not_enough():
    plan = {"resource_changes": [_rc("a.b", ["create"], {"tags": {"tenant_id": "ten-001"}})]}
    assert find_untagged(plan) == ["a.b"]


def test_check_is_generic_across_resource_types():
    plan = {"resource_changes": [
        _rc("aws_sqs_queue.q", ["create"], {"tags": {}}),
        _rc("aws_dynamodb_table.t", ["update"], {"tags": None}),
        _rc("aws_instance.i", ["delete", "create"], {"tags": {"landlord_account_id": "la-001"}}),
    ]}
    assert find_untagged(plan) == ["aws_dynamodb_table.t", "aws_sqs_queue.q"]


def test_empty_tag_value_counts_as_missing():
    plan = {"resource_changes": [_rc("a.b", ["create"], {"tags": {"landlord_account_id": ""}})]}
    assert find_untagged(plan) == ["a.b"]


def test_provider_default_tags_count():
    after = {"tags": {}, "tags_all": {"landlord_account_id": "la-001"}}
    assert find_untagged({"resource_changes": [_rc("a.b", ["create"], after)]}) == []


def test_skips_noop_read_delete_and_untaggable():
    plan = {"resource_changes": [
        _rc("a.noop", ["no-op"], {"tags": {}}),
        _rc("a.read", ["read"], {"tags": {}}),
        _rc("a.gone", ["delete"], None),
        _rc("a.untaggable", ["create"], {"name": "no tags attribute"}),
    ]}
    assert find_untagged(plan) == []
    assert check_plan_data(plan)[0] == 0


def test_idempotent_on_in_memory_plan():
    plan = {"resource_changes": [
        _rc("z.last", ["create"], {"tags": {}}),
        _rc("a.first", ["create"], {"tags": {}}),
    ]}
    assert check_plan_data(plan) == check_plan_data(plan)
    assert find_untagged(plan) == ["a.first", "z.last"]  # sorted, not input order


def test_idempotent_on_fixture_file(capsys):
    first_code = check_plan(FIXTURE)
    first_out = capsys.readouterr().out
    second_code = check_plan(FIXTURE)
    second_out = capsys.readouterr().out

    assert first_code == second_code == 1
    assert first_out == second_out
    assert first_out.count("aws_s3_bucket.listing_media") == 1  # no duplicated lines


def test_fingerprint_is_stable_and_order_of_keys_independent():
    a = {"resource_changes": [{"address": "x", "change": {"actions": ["create"]}}]}
    b = {"resource_changes": [{"change": {"actions": ["create"]}, "address": "x"}]}
    assert plan_fingerprint(a) == plan_fingerprint(b)
    c = {"resource_changes": [{"address": "y", "change": {"actions": ["create"]}}]}
    assert plan_fingerprint(a) != plan_fingerprint(c)
