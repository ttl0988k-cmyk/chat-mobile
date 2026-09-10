-- ============================================================
-- DAON Supabase Schema (2026-08-12)
-- 실행 위치: Supabase Dashboard → SQL Editor → New query → 붙여넣기 → Run
--
-- 설계 원칙:
--   1) RLS 켜기 → anon key로는 직접 INSERT 불가
--   2) 다온 서버(server.exe)가 service_role로만 데이터 쓰기
--   3) 모바일 라이트 UI는 anon key + 본인 user_id 필터로만 자기 데이터 조회
--   4) 대표님 1인용이지만, 멀티 디바이스/멀티 세션 대비
-- ============================================================

-- ============================================================
-- 1) conversations : 세션 1개 = 대화 1줄
-- ============================================================
create table if not exists public.conversations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  device      text not null,                       -- "집 데스크탑" / "아이폰" 등
  title       text,                                -- 첫 메시지 50자 자동 생성
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  ended_at    timestamptz,                         -- 세션 종료 시점 (옵션)
  metadata    jsonb default '{}'::jsonb            -- 디바이스/OS/해상도 등
);

create index if not exists idx_conv_user_updated
  on public.conversations(user_id, updated_at desc);

-- ============================================================
-- 2) messages : 채팅 메시지 1개
-- ============================================================
create table if not exists public.messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id         uuid references auth.users(id) on delete cascade,
  role            text not null check (role in ('user','assistant','system','tool')),
  content         text not null,
  token_count     integer,                         -- 옵션: OpenAI 토큰 카운트
  metadata        jsonb default '{}'::jsonb,       -- tool calls, attachments 등
  created_at      timestamptz not null default now()
);

create index if not exists idx_msg_conv_time
  on public.messages(conversation_id, created_at asc);
create index if not exists idx_msg_user_time
  on public.messages(user_id, created_at desc);

-- ============================================================
-- 3) agent_memory : 라온 영구 메모리 (지금 메모리 휘발성 문제 해결)
-- ============================================================
create table if not exists public.agent_memory (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  target      text not null check (target in ('memory','user','skill')), -- 어느 저장소인지
  key         text,                                -- 사실의 카테고리/키
  content     text not null,                       -- 실제 내용
  source      text,                                -- 'self' / 'user-explicit' / 'auto-extract'
  confidence  numeric(3,2) default 1.00 check (confidence between 0 and 1),
  metadata    jsonb default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists idx_mem_user_target
  on public.agent_memory(user_id, target);
create index if not exists idx_mem_key
  on public.agent_memory(key) where key is not null;

-- ============================================================
-- 4) agent_skills : 스킬 메타데이터
-- ============================================================
create table if not exists public.agent_skills (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references auth.users(id) on delete cascade,
  name         text not null,
  category     text,                                -- 'devops', 'creative' 등
  description  text,
  body         text,                                -- SKILL.md 본문
  use_count    integer not null default 0,
  last_used_at timestamptz,
  metadata     jsonb default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique(user_id, name)
);

create index if not exists idx_skills_user_cat
  on public.agent_skills(user_id, category);

-- ============================================================
-- 5) style_cards : 다온 디자인 카드 (Creative Director 연동)
-- ============================================================
create table if not exists public.style_cards (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references auth.users(id) on delete cascade,
  source        text,                              -- 'stripe', 'linear', 'manual' 등
  url           text,
  title         text not null,
  category      text,                              -- 'landing-page', 'dashboard' 등
  tags          text[] default '{}',                      -- ['glassmorphism','dark-mode']
  design_dna    jsonb default '{}'::jsonb,          -- 색상/타이포/스페이싱 DNA
  components    jsonb default '{}'::jsonb,          -- 컴포넌트 분해
  evaluation    jsonb default '{}'::jsonb,          -- 트렌드/접근성 점수
  screenshot_url text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists idx_cards_user_cat
  on public.style_cards(user_id, category);
create index if not exists idx_cards_tags
  on public.style_cards using gin(tags);

-- ============================================================
-- updated_at 자동 갱신 트리거
-- ============================================================
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end
$$;

do $$
declare
  t text;
begin
  for t in
    select unnest(array['conversations','agent_memory','agent_skills','style_cards'])
  loop
    execute format(
      'drop trigger if exists trg_%I_touch on public.%I;
       create trigger trg_%I_touch before update on public.%I
       for each row execute function public.touch_updated_at();',
      t, t, t, t
    );
  end loop;
end $$;

-- ============================================================
-- RLS (Row Level Security) — anon key로는 직접 쓰기 불가
-- ============================================================

-- 모든 테이블 RLS 켜기
alter table public.conversations enable row level security;
alter table public.messages      enable row level security;
alter table public.agent_memory  enable row level security;
alter table public.agent_skills  enable row level security;
alter table public.style_cards   enable row level security;

-- 대표님 user_id만 자기 데이터 조회 가능 (anon key + 로그인 상태)
-- user_id 컬럼이 자기 id와 일치할 때만 select 허용
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

-- INSERT/UPDATE/DELETE 는 anon key 정책 없음
-- → service_role 키(다온 서버) 만 가능
-- 모바일 라이트 UI에서 메시지 보내려면 → 다온 9090 프록시 경유 (안전)

-- ============================================================
-- 검증 쿼리 (실행 후 확인용)
-- ============================================================
-- select table_name from information_schema.tables
--   where table_schema='public' and table_name in
--   ('conversations','messages','agent_memory','agent_skills','style_cards');
-- 기대 결과: 5 rows