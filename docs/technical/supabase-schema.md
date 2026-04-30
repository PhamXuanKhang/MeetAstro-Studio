# Supabase Schema and RLS

This project now treats Supabase Auth user IDs as the source of truth for
user-owned data. Alembic revision `0003_supabase_rls_foundation.py` adds the
Supabase-compatible foundation.

## Ownership Rule

Every user-owned table has:

```sql
user_id uuid references auth.users(id)
```

RLS is enabled and forced on these tables:

- `meetings`
- `transcripts`
- `analysis_results`
- `review_items`
- `provider_configs`
- `user_plans`
- `usage_records`
- `jira_configs`
- `ai_jobs`
- `jira_push_records`
- `audit_logs`

Baseline policy:

```sql
using (user_id = auth.uid())
with check (user_id = auth.uid())
```

This means authenticated user A can only read, insert, update, or delete rows
whose `user_id` equals A's Supabase Auth UID. User B cannot access user A's
meeting, review, Jira config, usage, job, or audit rows through normal RLS-bound
queries.

## Child Row Ownership

The migration adds `user_id` to child tables instead of relying on joins for
policy checks:

- `transcripts`
- `analysis_results`
- `review_items`
- `usage_records`

Database triggers fill or validate child ownership:

- Meeting child rows copy `user_id` from `meetings`.
- `usage_records` copy `user_id` from `user_plans`.
- Transcript and analysis rows can reference `ai_jobs`; the trigger rejects
  rows where job owner, meeting owner, and row owner disagree.
- Jira push records validate meeting owner, optional AI job owner, and optional
  Jira config owner.

## Jira Configs

`jira_configs` is per-user and prepared for encrypted storage:

- Metadata: `site_url`, `project_key`, `cloud_id`, `active`, `metadata`
- Encrypted fields: `account_email_encrypted`, `api_token_encrypted`
- Unique scope: `(user_id, site_url, project_key)`

Desktop/client code must not receive service-role keys or plaintext Jira
tokens. Query `jira_config_metadata` when only config metadata is needed; that
view omits encrypted credential columns and uses invoker security so table RLS
still applies.

## Local PostgreSQL Compatibility

Supabase provides `auth.users` and `auth.uid()`. The migration creates a minimal
local fallback only when those objects do not already exist, so Alembic can still
run against a plain PostgreSQL database.

Existing legacy `user_id` values that are not UUID strings are converted to the
nil UUID during migration so old local rows do not block type conversion. New
production rows should always use the authenticated Supabase UID.

## Apply

```bash
alembic upgrade head
```

For Supabase, set `POSTGRES_URL` to the Supabase PostgreSQL connection string
before running Alembic. Do not put service-role keys in desktop or frontend
configuration.
