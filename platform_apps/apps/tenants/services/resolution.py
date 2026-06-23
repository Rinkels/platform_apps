# apps/tenants/services/resolution.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from django.db import transaction

from platform_apps.apps.accounts.models import UserContext, Membership
from platform_apps.apps.tenants.models import Tenant, LegalEntity


@dataclass(frozen=True)
class ResolvedScope:
    user_context: Optional[UserContext]
    tenant: Optional[Tenant]
    legal_entity: Optional[LegalEntity]
    changed: bool  # whether we auto-corrected and saved context


def get_or_create_user_context(user) -> Optional[UserContext]:
    if not user or not user.is_authenticated:
        return None
    try:
        return user.context
    except UserContext.DoesNotExist:
        return UserContext.objects.create(user=user)


def _get_active_memberships(user) -> "models.QuerySet[Membership]":
    return (
        Membership.objects
        .select_related("tenant")
        .filter(user=user, is_active=True)
        .order_by("tenant__slug", "id")
    )


def _pick_default_tenant(memberships) -> Optional[Tenant]:
    m = memberships.first()
    return m.tenant if m else None


def _membership_for_tenant(memberships, tenant: Tenant) -> Optional[Membership]:
    for m in memberships:
        if m.tenant_id == tenant.id:
            return m
    return None


def _allowed_legal_entities_for_membership(membership: Membership, tenant: Tenant):
    """
    If membership.legal_entities is empty => allow ALL tenant legal entities.
    If membership.legal_entities has rows => allow only those.
    """
    qs = membership.legal_entities.all()
    if qs.exists():
        return qs.filter(tenant=tenant)
    return LegalEntity.objects.filter(tenant=tenant)


def _pick_default_legal_entity(membership: Membership, tenant: Tenant) -> Optional[LegalEntity]:
    return _allowed_legal_entities_for_membership(membership, tenant).order_by("id").first()


@transaction.atomic
def resolve_scope_for_user(user, *, persist: bool = True) -> ResolvedScope:
    """
    Canonical scope resolver with safe defaults.

    persist=True will save corrected context back to UserContext.
    """
    ctx = get_or_create_user_context(user)
    if not ctx:
        return ResolvedScope(user_context=None, tenant=None, legal_entity=None, changed=False)

    memberships = list(_get_active_memberships(user))
    if not memberships:
        # User has no tenant access
        if persist and (ctx.active_tenant_id or ctx.active_legal_entity_id):
            ctx.active_tenant = None
            ctx.active_legal_entity = None
            ctx.save(update_fields=["active_tenant", "active_legal_entity"])
            return ResolvedScope(user_context=ctx, tenant=None, legal_entity=None, changed=True)
        return ResolvedScope(user_context=ctx, tenant=None, legal_entity=None, changed=False)

    changed = False

    # --- Tenant resolution ---
    tenant = ctx.active_tenant
    membership = None

    if tenant:
        membership = _membership_for_tenant(memberships, tenant)

    if not tenant or not membership:
        tenant = _pick_default_tenant(_get_active_memberships(user))
        membership = _membership_for_tenant(memberships, tenant) if tenant else None
        if tenant != ctx.active_tenant:
            changed = True

    # --- LegalEntity resolution ---
    legal_entity = ctx.active_legal_entity
    if tenant and membership:
        allowed_qs = _allowed_legal_entities_for_membership(membership, tenant)

        if legal_entity:
            # Must belong to the active tenant AND be allowed by membership
            if legal_entity.tenant_id != tenant.id:
                legal_entity = None
                changed = True
            elif not allowed_qs.filter(id=legal_entity.id).exists():
                legal_entity = None
                changed = True

        if not legal_entity:
            legal_entity = _pick_default_legal_entity(membership, tenant)
            if legal_entity != ctx.active_legal_entity:
                changed = True
    else:
        # No valid tenant => no legal entity
        if legal_entity is not None:
            legal_entity = None
            changed = True

    # --- Persist corrected context ---
    if persist and changed:
        ctx.active_tenant = tenant
        ctx.active_legal_entity = legal_entity
        ctx.save(update_fields=["active_tenant", "active_legal_entity"])

    return ResolvedScope(user_context=ctx, tenant=tenant, legal_entity=legal_entity, changed=changed)
