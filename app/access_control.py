"""
B2, part 1 — implement can_access_screening_report().

Read README.md's domain model first. A ScreeningReport belongs to a Tenant, a Tenant belongs to
a Property, and a Property belongs to a LandlordAccount. A PropertyManager is scoped to exactly
one LandlordAccount.

The LandlordAccount is the boundary that gates access: a manager may view a report only when
the report's tenant sits on a property owned by the manager's own landlord account.
"""
from app.models import PropertyManager, ScreeningReport, Property, Tenant


def can_access_screening_report(
    actor: PropertyManager,
    report: ScreeningReport,
    *,
    properties: list[Property],
    tenants: list[Tenant],
) -> bool:
    """
    actor: the PropertyManager requesting access
    report: the ScreeningReport they're trying to view
    properties: all known Property records
    tenants: all known Tenant records

    Return True if actor may view report, False otherwise. Fail closed — if anything needed to
    make this determination is missing (tenant not found, property not found), return False.
    """
    if not actor.landlord_account_id:
        return False

    tenant = next((t for t in tenants if t.id == report.tenant_id), None)
    if tenant is None:
        return False

    prop = next((p for p in properties if p.id == tenant.property_id), None)
    if prop is None or not prop.landlord_account_id:
        return False

    return prop.landlord_account_id == actor.landlord_account_id
