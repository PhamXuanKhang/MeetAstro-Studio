-- Phase 1: local work progress status for action items.
-- Apply this SQL in Supabase before enabling the UI for status updates.

alter table public.action_items
  add column if not exists work_status text not null default 'todo';

alter table public.action_items
  add column if not exists work_status_note text;

alter table public.action_items
  add column if not exists work_status_updated_at timestamp with time zone;

update public.action_items
set work_status = 'todo'
where work_status is null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'action_items_work_status_check'
  ) then
    alter table public.action_items
      add constraint action_items_work_status_check
      check (work_status in ('todo', 'in_progress', 'blocked', 'done', 'cancelled'));
  end if;
end $$;

create index if not exists ix_action_items_work_status
  on public.action_items(work_status);

create index if not exists ix_action_items_meeting_work_status
  on public.action_items(meeting_id, work_status);
