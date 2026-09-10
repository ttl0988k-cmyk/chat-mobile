-- ============================================================
-- 다온 모바일 앱 즉시 보안 강화 (2026-08-28 새벽, 대표님 지시)
-- 실행 위치: Supabase Dashboard → SQL Editor
-- ============================================================
-- 의도: "내 아이디/비번 말고는 다 막아"
-- 결과: anon은 로그인된 본인 user_id의 row만 SELECT 가능
--       INSERT/UPDATE/DELETE는 service_role(다온 서버)만 가능
--       신규 가입은 Dashboard에서 별도 OFF
-- ============================================================

-- 1) 기존 self_select 정책 유지 (있으면 재실행 안전)
do $$
declare
  t text;
begin
  for t in
    select unnest(array['conversations','messages','agent_memory','agent_skills','style_cards'])
  loop
    execute format(
      'drop policy if exists "self_select" on public.%I;
       create policy "self_select" on public.%I
       for select using (auth.uid() = user_id);',
      t, t
    );
  end loop;
end $$;

-- 2) anon은 public 스키마 테이블에 SELECT/INSERT/UPDATE/DELETE 전부 불가
--    (service_role은 RLS 우회, 다온 서버만 사용)
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
revoke execute on all functions in schema public from anon;

-- 3) authenticated(로그인된 본인)는 자기 user_id 행만 CRUD 가능
--    INSERT/UPDATE/DELETE는 anon으로 못 함 (이게 추가 잠금)
do $$
declare
  t text;
begin
  for t in
    select unnest(array['conversations','messages','agent_memory','agent_skills','style_cards'])
  loop
    -- INSERT: 자기 user_id로만
    execute format(
      'drop policy if exists "self_insert" on public.%I;
       create policy "self_insert" on public.%I
       for insert with check (auth.uid() = user_id);',
      t, t
    );
    -- UPDATE: 자기 user_id만
    execute format(
      'drop policy if exists "self_update" on public.%I;
       create policy "self_update" on public.%I
       for update using (auth.uid() = user_id)
                    with check (auth.uid() = user_id);',
      t, t
    );
    -- DELETE: 자기 user_id만
    execute format(
      'drop policy if exists "self_delete" on public.%I;
       create policy "self_delete" on public.%I
       for delete using (auth.uid() = user_id);',
      t, t
    );
  end loop;
end $$;

-- 4) Realtime PUBLICATION은 자기 행만 흘러나가도록 그대로 유지
--    (RLS가 Realtime에도 적용됨 — 추가 작업 불필요)

-- ============================================================
-- 검증 (실행 후 이 4개 쿼리 돌려서 확인)
-- ============================================================

-- (A) 정책 목록
-- select tablename, policyname, cmd, qual
--   from pg_policies where schemaname='public'
--   order by tablename, policyname;
-- 기대: 각 테이블마다 self_select / self_insert / self_update / self_delete 4개씩 = 20개

-- (B) anon 권한 박혔는지
-- select grantee, privilege_type, table_name
--   from information_schema.table_privileges
--   where grantee='anon' and table_schema='public';
-- 기대: 0 rows (anon은 테이블 권한 없음)

-- (C) 로그인 안 한 상태(anon)로 SELECT 시도하면 0행
-- (Supabase anon key 그대로 써서 /rest/v1/conversations GET 하면 [])

-- (D) 신규 가입 OFF 확인
-- Dashboard → Authentication → Providers → Email
-- "Confirm email" OFF + "Allow new users to sign up" OFF 둘 다 체크
-- 신규 가입 시도: 401 user_not_found 또는 signups disabled 에러
