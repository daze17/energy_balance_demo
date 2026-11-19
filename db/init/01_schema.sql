-- Энержи Баланс — өгөгдлийн сангийн бүтэц (Supabase-ийн оронд локал PostgreSQL)

CREATE SCHEMA IF NOT EXISTS n8n;   -- n8n өөрийн хүснэгтүүдийг энд хадгална

CREATE TABLE admin_users (
  id            SERIAL PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL DEFAULT 'Админ',
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE services (
  id            SERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  short_desc    TEXT NOT NULL,
  description   TEXT NOT NULL,
  price_from    BIGINT,              -- ₮, NULL = үнэгүй / тохиролцоно
  price_note    TEXT,
  duration      TEXT,
  icon          TEXT NOT NULL DEFAULT 'bolt',
  active        BOOLEAN NOT NULL DEFAULT true,
  sort_order    INT NOT NULL DEFAULT 0
);

CREATE TABLE staff (
  id         SERIAL PRIMARY KEY,
  name       TEXT NOT NULL,
  role       TEXT NOT NULL,
  email      TEXT,
  phone      TEXT,
  active     BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE bookings (
  id                 SERIAL PRIMARY KEY,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  name               TEXT NOT NULL,
  phone              TEXT,
  email              TEXT,
  company            TEXT,
  service_id         INT REFERENCES services(id) ON DELETE SET NULL,
  building_type      TEXT,
  message            TEXT,
  preferred_date     DATE,
  source             TEXT NOT NULL DEFAULT 'web',      -- web | chat | phone
  status             TEXT NOT NULL DEFAULT 'Шинэ',      -- Шинэ | Илгээсэн | Батлагдсан | Татгалзсан
  assigned_staff_id  INT REFERENCES staff(id) ON DELETE SET NULL,
  confirmation_email TEXT,
  confirmed_at       TIMESTAMPTZ
);

CREATE TABLE faq (
  id        SERIAL PRIMARY KEY,
  category  TEXT NOT NULL,
  question  TEXT NOT NULL,
  answer    TEXT NOT NULL
);

CREATE TABLE projects (
  id          SERIAL PRIMARY KEY,
  title       TEXT NOT NULL,
  client_type TEXT NOT NULL,
  year        INT,
  result      TEXT NOT NULL
);

CREATE TABLE posts (
  id           SERIAL PRIMARY KEY,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  topic        TEXT,
  caption      TEXT NOT NULL,
  slides       JSONB NOT NULL DEFAULT '[]',
  status       TEXT NOT NULL DEFAULT 'Хүлээгдэж буй',  -- Хүлээгдэж буй | Нийтэлсэн | Татгалзсан
  source       TEXT NOT NULL DEFAULT 'ai',
  published_at TIMESTAMPTZ,
  likes        INT NOT NULL DEFAULT 0,
  fb_post_id   TEXT                    -- бодит Facebook Page дээрх постын ID (холбогдсон үед)
);

CREATE TABLE chat_messages (
  id         SERIAL PRIMARY KEY,
  session_id TEXT NOT NULL,
  role       TEXT NOT NULL,          -- user | assistant
  content    TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON chat_messages(session_id, created_at);

CREATE TABLE energy_reports (
  id               SERIAL PRIMARY KEY,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  client_name      TEXT NOT NULL,
  email            TEXT,
  company          TEXT,
  building_type    TEXT NOT NULL,
  area_m2          NUMERIC NOT NULL,
  elec_kwh_year    NUMERIC NOT NULL,
  heat_gcal_year   NUMERIC NOT NULL DEFAULT 0,
  elec_cost_year   NUMERIC,
  heat_cost_year   NUMERIC,
  metrics          JSONB NOT NULL DEFAULT '{}',
  recommendations  TEXT,
  status           TEXT NOT NULL DEFAULT 'Бэлэн'
);

-- AI агент бүрийн ажиллалтын бүртгэл (самбар дээрх "үр дүнг тоогоор" хэсэг)
CREATE TABLE agent_runs (
  id          SERIAL PRIMARY KEY,
  agent       TEXT NOT NULL,          -- booking | chat | content | energy
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  duration_ms INT,
  status      TEXT NOT NULL,          -- success | error
  input       JSONB,
  output      JSONB,
  error       TEXT
);
CREATE INDEX ON agent_runs(agent, started_at DESC);
