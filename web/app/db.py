"""PostgreSQL холболт (Supabase-ийн оронд локал Postgres)."""
import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

DATABASE_URL = os.environ["DATABASE_URL"]


@contextmanager
def conn():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True) as c:
        yield c


def all(sql: str, params=None) -> list[dict]:
    with conn() as c:
        return c.execute(sql, params or ()).fetchall()


def one(sql: str, params=None) -> dict | None:
    with conn() as c:
        return c.execute(sql, params or ()).fetchone()


def run(sql: str, params=None) -> None:
    with conn() as c:
        c.execute(sql, params or ())


__all__ = ["all", "one", "run", "Jsonb"]


def init_schema(sql_dir: str) -> None:
    """Хоосон өгөгдлийн санд (Railway гэх мэт) schema + демо өгөгдлийг нэг удаа ачаална.
    Локал Docker-т Postgres өөрөө db/init-ийг ажиллуулдаг тул энд алгасна."""
    import glob

    files = sorted(glob.glob(f"{sql_dir}/*.sql"))
    if not files:
        return
    with conn() as c:
        c.execute("SELECT pg_advisory_lock(4747)")  # олон worker зэрэг ачаалахаас сэргийлнэ
        try:
            if c.execute("SELECT to_regclass('public.services') IS NOT NULL AS ok").fetchone()["ok"]:
                return
            for f in files:
                with open(f, encoding="utf-8") as fh:
                    c.execute(fh.read())
            print(f"DB schema + seed ачаалагдлаа: {len(files)} файл", flush=True)
        finally:
            c.execute("SELECT pg_advisory_unlock(4747)")
