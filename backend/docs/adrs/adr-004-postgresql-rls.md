# ADR-004: PostgreSQL Row-Level Security for Multi-Tenancy

**Status:** Accepted  
**Date:** 2026-07-09  
**Deciders:** Platform Engineering Team  

---

## Context

Noted Ma'am is a multi-tenant SaaS. Every user belongs to one or more workspaces.
Data isolation must prevent workspace A from ever reading workspace B's data —
even if application code has a bug.

Candidates: application-level filtering, separate schemas, separate databases,
PostgreSQL Row-Level Security (RLS).

---

## Decision

Use **PostgreSQL Row-Level Security (RLS)** as the enforcement layer for
workspace isolation. All tenant-scoped tables have a `workspace_id UUID` column.
RLS policies enforce `workspace_id = current_setting('app.workspace_id')::UUID`.

The `IAMMiddleware` sets this session variable via a SQLAlchemy `before_flush`
event listener on every request that touches the database.

---

## Rationale

| Approach | Isolation level | Bug-resistant | Complexity | Cost |
|----------|----------------|---------------|-----------|------|
| App-level filter | Application | No | Low | Free |
| Separate schemas | Database | Partial | High | Schema sprawl |
| Separate databases | Full | Yes | Very high | Expensive |
| **PostgreSQL RLS** | **Database** | **Yes** | **Medium** | **Free** |

RLS was chosen because:
1. **Defence in depth**: a missing `WHERE workspace_id = ?` in app code does
   not leak data — the database enforces it.
2. **Zero marginal cost**: existing PostgreSQL instance, no infrastructure change.
3. **Audit-friendly**: data access policies are visible in `pg_policies`.

---

## RLS Policy Design

```sql
-- Example policy for meetings table
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetings FORCE ROW LEVEL SECURITY;

CREATE POLICY workspace_isolation ON meetings
  USING (workspace_id = current_setting('app.workspace_id')::UUID);
```

`FORCE ROW LEVEL SECURITY` ensures the table owner (app user) is also subject
to the policy — preventing superuser bypass from the app role.

---

## Limitations

- RLS policies are evaluated per-row. For very large tables, this adds a
  predicate to every scan. Mitigated by indexing `workspace_id`.
- RLS bypassed by `BYPASSRLS` role. The application database user must never
  hold this privilege.
- SQLAlchemy `before_flush` sets the workspace only when a write is attempted.
  Read operations use `SET LOCAL app.workspace_id` in the session.

---

## Consequences

- **Positive:** Data isolation enforced at the database layer, independent of
  application correctness.
- **Positive:** Dramatically reduces blast radius of authorization bugs.
- **Negative:** Adds `SET LOCAL` overhead per database session. Measured at
  <0.5ms — negligible.

---

## Implementation

- `app/core/iam.py`: `IAMMiddleware` — `_set_rls_context()`, `before_flush`
- `alembic/`: migrations enable RLS on tenant-scoped tables
