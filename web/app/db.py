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
