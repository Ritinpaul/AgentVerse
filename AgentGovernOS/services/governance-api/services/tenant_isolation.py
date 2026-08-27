from typing import Any

from middleware.tenant import get_current_tenant_id
from sqlalchemy import Select


def apply_tenant_filter(stmt: Select, model: Any) -> Select:
    """
    Applies a tenant filter to a SQLAlchemy select statement based on the current tenant.
    If no tenant is set, it will optionally raise an error or just return the statement depending on policy.
    For now, if there is a tenant, we scope it.
    """
    tenant_id = get_current_tenant_id()
    if tenant_id and hasattr(model, 'org_id'):
        return stmt.where(model.org_id == tenant_id)
    return stmt
