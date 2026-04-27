"""
Table-level constants and helpers.

`GLOBAL_TABLES` is intentionally empty for now (your request).
Add table names here when you want them to be treated as truly global (not org-scoped).
"""

GLOBAL_TABLES: set[str] = {'stripe_webhook_events', 'stripe_catalog_items'}

# These are global by definition in this template (identity + tenants).
# Keep this separate from `GLOBAL_TABLES` so you can keep it empty while still
# having working defaults.
BUILTIN_GLOBAL_TABLES: set[str] = {'users', 'organizations'}


def is_global_table(table: str) -> bool:
    return table in BUILTIN_GLOBAL_TABLES or table in GLOBAL_TABLES
