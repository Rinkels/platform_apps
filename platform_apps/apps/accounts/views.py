# apps/accounts/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse

from .models import Membership, UserContext
from platform_apps.apps.tenants.models import Tenant, LegalEntity

@login_required
def switch_context(request: HttpRequest) -> HttpResponse:
    memberships = (
        Membership.objects
        .filter(user=request.user, is_active=True)
        .select_related("tenant")
        .prefetch_related("legal_entities")
        .order_by("tenant__name")
    )

    tenant_choices = [m.tenant for m in memberships]

    # Load current context for GET defaults
    ctx, _ = UserContext.objects.get_or_create(user=request.user)

    next_url = request.GET.get("next") or request.POST.get("next") or "/dashboard/"

    if request.method == "POST":
        selected_tenant_id = request.POST.get("tenant_id") or ""
        selected_legal_entity_id = request.POST.get("legal_entity_id") or ""
        intent = request.POST.get("intent") or "set"
    else:
        selected_tenant_id = str(ctx.active_tenant_id) if ctx.active_tenant_id else ""
        selected_legal_entity_id = str(ctx.active_legal_entity_id) if ctx.active_legal_entity_id else ""
        intent = "refresh"

    selected_tenant = None
    if selected_tenant_id:
        selected_tenant = next((t for t in tenant_choices if str(t.id) == str(selected_tenant_id)), None)

    allowed_legal_entities = []
    if selected_tenant:
        m = memberships.filter(tenant=selected_tenant).first()
        if m:
            if m.legal_entities.exists():
                allowed_legal_entities = list(m.legal_entities.all().order_by("code"))
            else:
                allowed_legal_entities = list(
                    LegalEntity.objects.filter(tenant=selected_tenant, is_active=True).order_by("code")
                )

    # POST handling
    if request.method == "POST":
        # If it's a refresh (tenant changed), do NOT save context.
        if intent == "refresh":
            return render(
                request,
                "accounts/switch_context.html",
                {
                    "memberships": memberships,
                    "tenant_choices": tenant_choices,
                    "allowed_legal_entities": allowed_legal_entities,
                    "selected_tenant_id": selected_tenant_id,
                    "selected_legal_entity_id": selected_legal_entity_id,
                    "next": next_url,
                },
            )

        # Real "set context"
        tenant = None
        if selected_tenant_id:
            tenant = Tenant.objects.filter(id=selected_tenant_id).first()

        # Must be a tenant the user belongs to
        if tenant and not memberships.filter(tenant=tenant).exists():
            tenant = None

        # Auto-select the only legal entity if user didn't choose one
        le_id = selected_legal_entity_id or None
        if tenant and not le_id and len(allowed_legal_entities) == 1:
            le_id = str(allowed_legal_entities[0].id)

        legal_entity = None
        if le_id and tenant:
            legal_entity = LegalEntity.objects.filter(id=le_id, tenant=tenant).first()

            m = memberships.filter(tenant=tenant).first()
            if (
                m and m.legal_entities.exists()
                and legal_entity
                and not m.legal_entities.filter(id=legal_entity.id).exists()
            ):
                legal_entity = None

        ctx.active_tenant = tenant
        ctx.active_legal_entity = legal_entity
        ctx.save(update_fields=["active_tenant", "active_legal_entity", "updated_at"])

        return redirect(next_url)

    # GET render
    return render(
        request,
        "accounts/switch_context.html",
        {
            "memberships": memberships,
            "tenant_choices": tenant_choices,
            "allowed_legal_entities": allowed_legal_entities,
            "selected_tenant_id": selected_tenant_id,
            "selected_legal_entity_id": selected_legal_entity_id,
            "next": next_url,
        },
    )

