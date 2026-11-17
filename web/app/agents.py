"""n8n дээрх AI агентуудыг webhook-оор дуудаж, ажиллалт бүрийг agent_runs-д бүртгэнэ."""
import os
import time

import httpx

from . import db

N8N = os.environ.get("N8N_WEBHOOK_BASE", "http://n8n:5678/webhook")

AGENTS = {
    "booking": {"path": "eb-booking", "name": "Захиалга баталгаажуулах агент", "minutes_saved": 10},
    "chat":    {"path": "eb-chat",    "name": "Харилцагчийн зөвлөх чат агент", "minutes_saved": 5},
    "content": {"path": "eb-content", "name": "Контент агент (Facebook)",       "minutes_saved": 45},
    "energy":  {"path": "eb-energy",  "name": "Эрчим хүчний шинжилгээний агент", "minutes_saved": 60},
}


def _log(agent: str, started: float, status: str, payload, output, error=None):
    db.run(
        "INSERT INTO agent_runs (agent, duration_ms, status, input, output, error) VALUES (%s,%s,%s,%s,%s,%s)",
        (agent, int((time.time() - started) * 1000), status, db.Jsonb(payload), db.Jsonb(output), error),
    )


def call(agent: str, payload: dict, timeout: float = 120) -> dict:
    """Агентыг синхрон дуудна. Алдаа гарвал {'error': ...} буцаана."""
    started = time.time()
    url = f"{N8N}/{AGENTS[agent]['path']}"
    try:
        r = httpx.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        out = r.json() if r.content else {}
        if isinstance(out, list):
            out = out[0] if out else {}
        _log(agent, started, "success", payload, out)
        return out
    except Exception as e:  # noqa: BLE001 — демо: алдааг самбарт харуулна
        msg = f"{type(e).__name__}: {e}"
        if isinstance(e, httpx.HTTPStatusError):
            msg += f" — {e.response.text[:300]}"
        _log(agent, started, "error", payload, None, msg)
        return {"error": msg}
