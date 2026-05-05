"""Add Supabase auth ownership and RLS foundation.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_TABLES = (
    "meetings",
    "transcripts",
    "analysis_results",
    "review_items",
    "provider_configs",
    "user_plans",
    "usage_records",
    "jira_configs",
    "ai_jobs",
    "jira_push_records",
    "audit_logs",
)


def _exec_each(*statements: str) -> None:
    """Một lệnh SQL mỗi execute — driver asyncpg không hỗ trợ multi-statement."""
    for stmt in statements:
        op.execute(stmt.strip())


def upgrade() -> None:
    _exec_each(
        """CREATE EXTENSION IF NOT EXISTS "pgcrypto";""",
        """CREATE SCHEMA IF NOT EXISTS auth;""",
        """CREATE TABLE IF NOT EXISTS auth.users (
            id uuid PRIMARY KEY
        );""",
        """DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'auth'
                  AND p.proname = 'uid'
                  AND p.pronargs = 0
            ) THEN
                EXECUTE $create_function$
                    CREATE FUNCTION auth.uid()
                    RETURNS uuid
                    LANGUAGE sql
                    STABLE
                    AS $func$
                        SELECT NULLIF(
                            current_setting('request.jwt.claim.sub', true), ''
                        )::uuid
                    $func$;
                $create_function$;
            END IF;
        END $$;""",
    )

    _exec_each(
        """ALTER TABLE public.meetings ALTER COLUMN user_id DROP DEFAULT;""",
        """ALTER TABLE public.provider_configs ALTER COLUMN user_id DROP DEFAULT;""",
        """ALTER TABLE public.meetings
            ALTER COLUMN user_id TYPE uuid
            USING (
                CASE
                    WHEN user_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                    THEN user_id::uuid
                    ELSE '00000000-0000-0000-0000-000000000000'::uuid
                END
            );""",
        """ALTER TABLE public.provider_configs
            ALTER COLUMN user_id TYPE uuid
            USING (
                CASE
                    WHEN user_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                    THEN user_id::uuid
                    ELSE '00000000-0000-0000-0000-000000000000'::uuid
                END
            );""",
        """ALTER TABLE public.user_plans
            ALTER COLUMN user_id TYPE uuid
            USING (
                CASE
                    WHEN user_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                    THEN user_id::uuid
                    ELSE '00000000-0000-0000-0000-000000000000'::uuid
                END
            );""",
        """ALTER TABLE public.meetings ALTER COLUMN user_id SET DEFAULT auth.uid();""",
        """ALTER TABLE public.provider_configs ALTER COLUMN user_id SET DEFAULT auth.uid();""",
        """ALTER TABLE public.user_plans ALTER COLUMN user_id SET DEFAULT auth.uid();""",
    )

    _exec_each(
        """ALTER TABLE public.transcripts ADD COLUMN user_id uuid;""",
        """ALTER TABLE public.analysis_results ADD COLUMN user_id uuid;""",
        """ALTER TABLE public.review_items ADD COLUMN user_id uuid;""",
        """ALTER TABLE public.usage_records ADD COLUMN user_id uuid;""",
        """ALTER TABLE public.transcripts ADD COLUMN ai_job_id uuid;""",
        """ALTER TABLE public.analysis_results ADD COLUMN ai_job_id uuid;""",
        """UPDATE public.transcripts t
        SET user_id = m.user_id
        FROM public.meetings m
        WHERE t.meeting_id = m.id;""",
        """UPDATE public.analysis_results a
        SET user_id = m.user_id
        FROM public.meetings m
        WHERE a.meeting_id = m.id;""",
        """UPDATE public.review_items r
        SET user_id = m.user_id
        FROM public.meetings m
        WHERE r.meeting_id = m.id;""",
        """UPDATE public.usage_records u
        SET user_id = p.user_id
        FROM public.user_plans p
        WHERE u.user_plan_id = p.id;""",
        """ALTER TABLE public.transcripts ALTER COLUMN user_id SET NOT NULL;""",
        """ALTER TABLE public.analysis_results ALTER COLUMN user_id SET NOT NULL;""",
        """ALTER TABLE public.review_items ALTER COLUMN user_id SET NOT NULL;""",
        """ALTER TABLE public.usage_records ALTER COLUMN user_id SET NOT NULL;""",
    )

    _exec_each(
        """ALTER TABLE public.meetings
            ADD CONSTRAINT fk_meetings_user
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE NOT VALID;""",
        """ALTER TABLE public.transcripts
            ADD CONSTRAINT fk_transcripts_user
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE NOT VALID;""",
        """ALTER TABLE public.analysis_results
            ADD CONSTRAINT fk_analysis_results_user
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE NOT VALID;""",
        """ALTER TABLE public.review_items
            ADD CONSTRAINT fk_review_items_user
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE NOT VALID;""",
        """ALTER TABLE public.provider_configs
            ADD CONSTRAINT fk_provider_configs_user
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE NOT VALID;""",
        """ALTER TABLE public.user_plans
            ADD CONSTRAINT fk_user_plans_user
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE NOT VALID;""",
        """ALTER TABLE public.usage_records
            ADD CONSTRAINT fk_usage_records_user
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE NOT VALID;""",
    )

    _exec_each(
        """CREATE TABLE public.jira_configs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
            site_url text NOT NULL,
            project_key text NOT NULL,
            account_email_encrypted text,
            api_token_encrypted text,
            cloud_id text,
            active boolean NOT NULL DEFAULT true,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_jira_configs_user_site_project
                UNIQUE (user_id, site_url, project_key)
        );""",
        """CREATE TABLE public.ai_jobs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
            meeting_id uuid REFERENCES public.meetings(id) ON DELETE CASCADE,
            job_type text NOT NULL,
            provider text,
            status text NOT NULL DEFAULT 'queued',
            celery_task_id text,
            input_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            result_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            error_message text,
            started_at timestamptz,
            finished_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );""",
        """ALTER TABLE public.transcripts
            ADD CONSTRAINT fk_transcripts_ai_job
            FOREIGN KEY (ai_job_id) REFERENCES public.ai_jobs(id) ON DELETE SET NULL;""",
        """ALTER TABLE public.analysis_results
            ADD CONSTRAINT fk_analysis_results_ai_job
            FOREIGN KEY (ai_job_id) REFERENCES public.ai_jobs(id) ON DELETE SET NULL;""",
        """CREATE TABLE public.jira_push_records (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
            meeting_id uuid NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
            ai_job_id uuid REFERENCES public.ai_jobs(id) ON DELETE SET NULL,
            jira_config_id uuid REFERENCES public.jira_configs(id) ON DELETE SET NULL,
            status text NOT NULL DEFAULT 'queued',
            is_stub boolean NOT NULL DEFAULT false,
            epic_keys jsonb NOT NULL DEFAULT '[]'::jsonb,
            epic_count integer NOT NULL DEFAULT 0,
            task_count integer NOT NULL DEFAULT 0,
            subtask_count integer NOT NULL DEFAULT 0,
            error_message text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );""",
        """CREATE TABLE public.audit_logs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
            action text NOT NULL,
            entity_type text NOT NULL,
            entity_id uuid,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            ip_address inet,
            user_agent text,
            created_at timestamptz NOT NULL DEFAULT now()
        );""",
        """CREATE INDEX ix_meetings_user_id ON public.meetings (user_id);""",
        """CREATE INDEX ix_transcripts_user_id ON public.transcripts (user_id);""",
        """CREATE INDEX ix_analysis_results_user_id ON public.analysis_results (user_id);""",
        """CREATE INDEX ix_review_items_user_id ON public.review_items (user_id);""",
        """CREATE INDEX ix_provider_configs_user_id ON public.provider_configs (user_id);""",
        """CREATE INDEX ix_usage_records_user_id ON public.usage_records (user_id);""",
        """CREATE INDEX ix_jira_configs_user_id ON public.jira_configs (user_id);""",
        """CREATE INDEX ix_ai_jobs_user_id_status ON public.ai_jobs (user_id, status);""",
        """CREATE INDEX ix_ai_jobs_meeting_id ON public.ai_jobs (meeting_id);""",
        """CREATE INDEX ix_jira_push_records_user_id ON public.jira_push_records (user_id);""",
        """CREATE INDEX ix_jira_push_records_meeting_id ON public.jira_push_records (meeting_id);""",
        """CREATE INDEX ix_audit_logs_user_id_created_at
            ON public.audit_logs (user_id, created_at DESC);""",
        """COMMENT ON TABLE public.jira_configs IS
            'Per-user Jira config metadata plus encrypted credential fields.';""",
        """COMMENT ON COLUMN public.jira_configs.account_email_encrypted IS
            'Encrypted Jira account email. Do not expose plaintext to desktop clients.';""",
        """COMMENT ON COLUMN public.jira_configs.api_token_encrypted IS
            'Encrypted Jira API token. Do not expose plaintext credentials.';""",
    )

    _exec_each(
        """CREATE FUNCTION public.enforce_meeting_user_id()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            owner_id uuid;
        BEGIN
            SELECT m.user_id INTO owner_id
            FROM public.meetings m
            WHERE m.id = NEW.meeting_id;

            IF owner_id IS NULL THEN
                RAISE EXCEPTION 'meeting % not found for user-owned row', NEW.meeting_id
                    USING ERRCODE = 'foreign_key_violation';
            END IF;

            IF NEW.user_id IS NULL THEN
                NEW.user_id = owner_id;
            ELSIF NEW.user_id <> owner_id THEN
                RAISE EXCEPTION 'row user_id % does not match meeting owner %',
                    NEW.user_id, owner_id
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NEW;
        END;
        $$;""",
        """CREATE FUNCTION public.enforce_meeting_job_user_id()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            owner_id uuid;
            job_owner_id uuid;
            job_meeting_id uuid;
        BEGIN
            SELECT m.user_id INTO owner_id
            FROM public.meetings m
            WHERE m.id = NEW.meeting_id;

            IF owner_id IS NULL THEN
                RAISE EXCEPTION 'meeting % not found for user-owned row', NEW.meeting_id
                    USING ERRCODE = 'foreign_key_violation';
            END IF;

            IF NEW.user_id IS NULL THEN
                NEW.user_id = owner_id;
            ELSIF NEW.user_id <> owner_id THEN
                RAISE EXCEPTION 'row user_id % does not match meeting owner %',
                    NEW.user_id, owner_id
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NEW.ai_job_id IS NOT NULL THEN
                SELECT j.user_id, j.meeting_id
                INTO job_owner_id, job_meeting_id
                FROM public.ai_jobs j
                WHERE j.id = NEW.ai_job_id;

                IF job_owner_id IS NULL THEN
                    RAISE EXCEPTION 'ai_job % not found', NEW.ai_job_id
                        USING ERRCODE = 'foreign_key_violation';
                END IF;

                IF job_owner_id <> NEW.user_id THEN
                    RAISE EXCEPTION 'ai_job user_id % does not match row user_id %',
                        job_owner_id, NEW.user_id
                        USING ERRCODE = 'check_violation';
                END IF;

                IF job_meeting_id IS NOT NULL AND job_meeting_id <> NEW.meeting_id THEN
                    RAISE EXCEPTION 'ai_job meeting_id % does not match row meeting_id %',
                        job_meeting_id, NEW.meeting_id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$;""",
        """CREATE FUNCTION public.enforce_usage_record_user_id()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            owner_id uuid;
        BEGIN
            SELECT p.user_id INTO owner_id
            FROM public.user_plans p
            WHERE p.id = NEW.user_plan_id;

            IF owner_id IS NULL THEN
                RAISE EXCEPTION 'user_plan % not found for usage record', NEW.user_plan_id
                    USING ERRCODE = 'foreign_key_violation';
            END IF;

            IF NEW.user_id IS NULL THEN
                NEW.user_id = owner_id;
            ELSIF NEW.user_id <> owner_id THEN
                RAISE EXCEPTION 'usage record user_id % does not match plan owner %',
                    NEW.user_id, owner_id
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NEW;
        END;
        $$;""",
        """CREATE FUNCTION public.enforce_ai_job_user_id()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            owner_id uuid;
        BEGIN
            IF NEW.meeting_id IS NOT NULL THEN
                SELECT m.user_id INTO owner_id
                FROM public.meetings m
                WHERE m.id = NEW.meeting_id;

                IF owner_id IS NULL THEN
                    RAISE EXCEPTION 'meeting % not found for ai_job', NEW.meeting_id
                        USING ERRCODE = 'foreign_key_violation';
                END IF;

                IF NEW.user_id <> owner_id THEN
                    RAISE EXCEPTION 'ai_job user_id % does not match meeting owner %',
                        NEW.user_id, owner_id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$;""",
        """CREATE FUNCTION public.enforce_jira_push_record_user_id()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            owner_id uuid;
            job_owner_id uuid;
            config_owner_id uuid;
        BEGIN
            SELECT m.user_id INTO owner_id
            FROM public.meetings m
            WHERE m.id = NEW.meeting_id;

            IF owner_id IS NULL THEN
                RAISE EXCEPTION 'meeting % not found for jira push record', NEW.meeting_id
                    USING ERRCODE = 'foreign_key_violation';
            END IF;

            IF NEW.user_id IS NULL THEN
                NEW.user_id = owner_id;
            ELSIF NEW.user_id <> owner_id THEN
                RAISE EXCEPTION 'jira push user_id % does not match meeting owner %',
                    NEW.user_id, owner_id
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NEW.ai_job_id IS NOT NULL THEN
                SELECT j.user_id INTO job_owner_id
                FROM public.ai_jobs j
                WHERE j.id = NEW.ai_job_id;

                IF job_owner_id IS NULL THEN
                    RAISE EXCEPTION 'ai_job % not found', NEW.ai_job_id
                        USING ERRCODE = 'foreign_key_violation';
                END IF;

                IF job_owner_id <> NEW.user_id THEN
                    RAISE EXCEPTION 'ai_job owner % does not match jira push owner %',
                        job_owner_id, NEW.user_id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            IF NEW.jira_config_id IS NOT NULL THEN
                SELECT c.user_id INTO config_owner_id
                FROM public.jira_configs c
                WHERE c.id = NEW.jira_config_id;

                IF config_owner_id IS NULL THEN
                    RAISE EXCEPTION 'jira_config % not found', NEW.jira_config_id
                        USING ERRCODE = 'foreign_key_violation';
                END IF;

                IF config_owner_id <> NEW.user_id THEN
                    RAISE EXCEPTION 'jira_config owner % does not match jira push owner %',
                        config_owner_id, NEW.user_id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$;""",
        """CREATE TRIGGER trg_transcripts_user_id
            BEFORE INSERT OR UPDATE OF user_id, meeting_id, ai_job_id
            ON public.transcripts
            FOR EACH ROW EXECUTE FUNCTION public.enforce_meeting_job_user_id();""",
        """CREATE TRIGGER trg_analysis_results_user_id
            BEFORE INSERT OR UPDATE OF user_id, meeting_id, ai_job_id
            ON public.analysis_results
            FOR EACH ROW EXECUTE FUNCTION public.enforce_meeting_job_user_id();""",
        """CREATE TRIGGER trg_review_items_user_id
            BEFORE INSERT OR UPDATE OF user_id, meeting_id
            ON public.review_items
            FOR EACH ROW EXECUTE FUNCTION public.enforce_meeting_user_id();""",
        """CREATE TRIGGER trg_usage_records_user_id
            BEFORE INSERT OR UPDATE OF user_id, user_plan_id
            ON public.usage_records
            FOR EACH ROW EXECUTE FUNCTION public.enforce_usage_record_user_id();""",
        """CREATE TRIGGER trg_ai_jobs_user_id
            BEFORE INSERT OR UPDATE OF user_id, meeting_id
            ON public.ai_jobs
            FOR EACH ROW EXECUTE FUNCTION public.enforce_ai_job_user_id();""",
        """CREATE TRIGGER trg_jira_push_records_user_id
            BEFORE INSERT OR UPDATE OF user_id, meeting_id, ai_job_id, jira_config_id
            ON public.jira_push_records
            FOR EACH ROW EXECUTE FUNCTION public.enforce_jira_push_record_user_id();""",
    )

    _exec_each(
        """CREATE VIEW public.jira_config_metadata
        WITH (security_invoker = true)
        AS
        SELECT
            id,
            user_id,
            site_url,
            project_key,
            cloud_id,
            active,
            metadata,
            created_at,
            updated_at
        FROM public.jira_configs;""",
    )

    _apply_rls()


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS public.jira_config_metadata")

    for table_name in USER_TABLES:
        _exec_each(
            f"DROP POLICY IF EXISTS user_is_owner ON public.{table_name};",
            f"ALTER TABLE IF EXISTS public.{table_name} DISABLE ROW LEVEL SECURITY;",
            f"ALTER TABLE IF EXISTS public.{table_name} NO FORCE ROW LEVEL SECURITY;",
        )

    _exec_each(
        """DROP TRIGGER IF EXISTS trg_jira_push_records_user_id ON public.jira_push_records;""",
        """DROP TRIGGER IF EXISTS trg_ai_jobs_user_id ON public.ai_jobs;""",
        """DROP TRIGGER IF EXISTS trg_usage_records_user_id ON public.usage_records;""",
        """DROP TRIGGER IF EXISTS trg_review_items_user_id ON public.review_items;""",
        """DROP TRIGGER IF EXISTS trg_analysis_results_user_id ON public.analysis_results;""",
        """DROP TRIGGER IF EXISTS trg_transcripts_user_id ON public.transcripts;""",
        """DROP FUNCTION IF EXISTS public.enforce_jira_push_record_user_id();""",
        """DROP FUNCTION IF EXISTS public.enforce_ai_job_user_id();""",
        """DROP FUNCTION IF EXISTS public.enforce_usage_record_user_id();""",
        """DROP FUNCTION IF EXISTS public.enforce_meeting_job_user_id();""",
        """DROP FUNCTION IF EXISTS public.enforce_meeting_user_id();""",
        """ALTER TABLE public.analysis_results DROP CONSTRAINT IF EXISTS fk_analysis_results_ai_job;""",
        """ALTER TABLE public.transcripts DROP CONSTRAINT IF EXISTS fk_transcripts_ai_job;""",
        """ALTER TABLE public.usage_records DROP CONSTRAINT IF EXISTS fk_usage_records_user;""",
        """ALTER TABLE public.user_plans DROP CONSTRAINT IF EXISTS fk_user_plans_user;""",
        """ALTER TABLE public.provider_configs DROP CONSTRAINT IF EXISTS fk_provider_configs_user;""",
        """ALTER TABLE public.review_items DROP CONSTRAINT IF EXISTS fk_review_items_user;""",
        """ALTER TABLE public.analysis_results DROP CONSTRAINT IF EXISTS fk_analysis_results_user;""",
        """ALTER TABLE public.transcripts DROP CONSTRAINT IF EXISTS fk_transcripts_user;""",
        """ALTER TABLE public.meetings DROP CONSTRAINT IF EXISTS fk_meetings_user;""",
        """DROP TABLE IF EXISTS public.audit_logs;""",
        """DROP TABLE IF EXISTS public.jira_push_records;""",
        """DROP TABLE IF EXISTS public.jira_configs;""",
        """DROP TABLE IF EXISTS public.ai_jobs;""",
        """DROP INDEX IF EXISTS public.ix_usage_records_user_id;""",
        """DROP INDEX IF EXISTS public.ix_provider_configs_user_id;""",
        """DROP INDEX IF EXISTS public.ix_review_items_user_id;""",
        """DROP INDEX IF EXISTS public.ix_analysis_results_user_id;""",
        """DROP INDEX IF EXISTS public.ix_transcripts_user_id;""",
        """DROP INDEX IF EXISTS public.ix_meetings_user_id;""",
        """ALTER TABLE public.analysis_results DROP COLUMN IF EXISTS ai_job_id;""",
        """ALTER TABLE public.transcripts DROP COLUMN IF EXISTS ai_job_id;""",
        """ALTER TABLE public.usage_records DROP COLUMN IF EXISTS user_id;""",
        """ALTER TABLE public.review_items DROP COLUMN IF EXISTS user_id;""",
        """ALTER TABLE public.analysis_results DROP COLUMN IF EXISTS user_id;""",
        """ALTER TABLE public.transcripts DROP COLUMN IF EXISTS user_id;""",
        """ALTER TABLE public.user_plans
            ALTER COLUMN user_id TYPE text USING user_id::text;""",
        """ALTER TABLE public.provider_configs
            ALTER COLUMN user_id TYPE text USING user_id::text;""",
        """ALTER TABLE public.meetings
            ALTER COLUMN user_id TYPE text USING user_id::text;""",
        """ALTER TABLE public.provider_configs ALTER COLUMN user_id SET DEFAULT 'default_user';""",
        """ALTER TABLE public.meetings ALTER COLUMN user_id SET DEFAULT 'default_user';""",
    )


def _apply_rls() -> None:
    for table_name in USER_TABLES:
        _exec_each(
            f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;",
            f"ALTER TABLE public.{table_name} FORCE ROW LEVEL SECURITY;",
            f"DROP POLICY IF EXISTS user_is_owner ON public.{table_name};",
            f"""CREATE POLICY user_is_owner
                ON public.{table_name}
                FOR ALL
                USING (user_id = auth.uid())
                WITH CHECK (user_id = auth.uid());""",
        )
