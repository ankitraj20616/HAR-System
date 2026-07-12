-- Milestone 6: Supabase Auth roles and custom JWT claim.
-- Run this in the Supabase SQL editor, then enable public.custom_access_token_hook
-- under Authentication > Hooks > Custom Access Token.

create type public.app_role as enum ('pending', 'caregiver', 'doctor', 'admin');

create table public.user_roles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    role public.app_role not null default 'pending',
    updated_at timestamptz not null default now(),
    updated_by uuid references auth.users(id) on delete set null
);

create table public.role_audit_log (
    id bigint generated always as identity primary key,
    user_id uuid not null,
    old_role public.app_role,
    new_role public.app_role not null,
    changed_by uuid,
    changed_at timestamptz not null default now()
);

alter table public.user_roles enable row level security;
alter table public.role_audit_log enable row level security;

-- Browsers must not read or write role assignment tables directly. The custom
-- token hook reads roles as supabase_auth_admin; backend administration uses
-- the server-only service_role key, which bypasses RLS.
revoke all on table public.user_roles from anon, authenticated, public;
revoke all on table public.role_audit_log from anon, authenticated, public;

create or replace function public.assign_pending_role()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.user_roles (user_id, role)
    values (new.id, 'pending')
    on conflict (user_id) do nothing;
    return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.assign_pending_role();

create or replace function public.audit_role_change()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if tg_op = 'INSERT' or old.role is distinct from new.role then
        insert into public.role_audit_log (user_id, old_role, new_role, changed_by)
        values (new.user_id, case when tg_op = 'UPDATE' then old.role else null end, new.role, new.updated_by);
    end if;
    new.updated_at := now();
    return new;
end;
$$;

create trigger user_role_audit
before insert or update on public.user_roles
for each row execute function public.audit_role_change();

create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    claims jsonb;
    assigned_role public.app_role;
begin
    select role into assigned_role
    from public.user_roles
    where user_id = (event->>'user_id')::uuid;

    claims := event->'claims';
    claims := jsonb_set(
        claims,
        '{user_role}',
        to_jsonb(coalesce(assigned_role, 'pending'::public.app_role))
    );
    return jsonb_set(event, '{claims}', claims);
end;
$$;

grant usage on schema public to supabase_auth_admin;
grant select on table public.user_roles to supabase_auth_admin;
grant execute on function public.custom_access_token_hook(jsonb) to supabase_auth_admin;
revoke execute on function public.custom_access_token_hook(jsonb) from anon, authenticated, public;

-- Existing Auth users (created before this migration) also start with no data access.
insert into public.user_roles (user_id, role)
select id, 'pending' from auth.users
on conflict (user_id) do nothing;
