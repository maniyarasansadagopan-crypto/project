"""
Write tests here proving:
  1. A PropertyManager scoped to la-001 (pm-001) is DENIED access to la-002's tenant's
     screening report (rep-002).
  2. The same PropertyManager (pm-001) IS allowed access to their own account's screening
     report (rep-001).

Use the `property_managers`, `properties`, `tenants`, and `screening_reports` fixtures from
conftest.py — don't re-invent the seed data here.
"""
from dataclasses import replace

from app.access_control import can_access_screening_report


def _by_id(items, item_id):
    return next(i for i in items if i.id == item_id)


def test_cross_account_access_is_denied(property_managers, properties, tenants, screening_reports):
    pm_001 = _by_id(property_managers, "pm-001")  # la-001
    rep_002 = _by_id(screening_reports, "rep-002")  # belongs to la-002's tenant

    assert can_access_screening_report(
        pm_001, rep_002, properties=properties, tenants=tenants
    ) is False


def test_same_account_access_is_allowed(property_managers, properties, tenants, screening_reports):
    pm_001 = _by_id(property_managers, "pm-001")
    rep_001 = _by_id(screening_reports, "rep-001")

    assert can_access_screening_report(
        pm_001, rep_001, properties=properties, tenants=tenants
    ) is True


def test_denial_is_symmetric(property_managers, properties, tenants, screening_reports):
    pm_002 = _by_id(property_managers, "pm-002")
    rep_001 = _by_id(screening_reports, "rep-001")
    rep_002 = _by_id(screening_reports, "rep-002")

    assert can_access_screening_report(pm_002, rep_001, properties=properties, tenants=tenants) is False
    assert can_access_screening_report(pm_002, rep_002, properties=properties, tenants=tenants) is True


def test_fails_closed_when_tenant_missing(property_managers, properties, screening_reports):
    pm_001 = _by_id(property_managers, "pm-001")
    rep_001 = _by_id(screening_reports, "rep-001")

    assert can_access_screening_report(pm_001, rep_001, properties=properties, tenants=[]) is False


def test_fails_closed_when_property_missing(property_managers, tenants, screening_reports):
    pm_001 = _by_id(property_managers, "pm-001")
    rep_001 = _by_id(screening_reports, "rep-001")

    assert can_access_screening_report(pm_001, rep_001, properties=[], tenants=tenants) is False


def test_fails_closed_when_actor_has_no_account(property_managers, properties, tenants, screening_reports):
    unscoped = replace(_by_id(property_managers, "pm-001"), landlord_account_id="")
    rep_001 = _by_id(screening_reports, "rep-001")

    assert can_access_screening_report(unscoped, rep_001, properties=properties, tenants=tenants) is False
