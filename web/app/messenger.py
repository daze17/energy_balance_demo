"""Facebook Messenger ↔ чат агент (Агент 2).

Facebook хуудас руу бичсэн мессеж → Meta webhook → энэ сервер → n8n чат агент → Graph API-аар хариу.
Вэб чаттай яг ижил агент, ижил санах ой (session = fb-<хэрэглэгчийн PSID>); яриа админ «Чат»-д харагдана.

Тохиргоо (.env / Railway variables):
  FB_VERIFY_TOKEN  — webhook баталгаажуулах дурын нууц үг (Meta-д мөн адил оруулна)
  FB_PAGE_TOKEN    — хуудасны Page access token (pages_messaging)
  FB_APP_SECRET    — (сонголттой) Meta app secret; байвал X-Hub-Signature-256 шалгана
"""
import hashlib
import hmac
import json
import os

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from . import agents, db

router = APIRouter()
VERIFY_TOKEN = os.environ.get("FB_VERIFY_TOKEN", "")
PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
APP_SECRET = os.environ.get("FB_APP_SECRET", "")
GRAPH = "https://graph.facebook.com/me/messages"
FALLBACK = "Уучлаарай, түр алдаа гарлаа. Та +976 8811 3855 дугаарт залгана уу."


def init():
    """Meta нэг мессежийг давтан илгээж болдог — mid-ээр давхардлыг шүүнэ (2 worker-т ч ажиллана)."""
    db.run("CREATE TABLE IF NOT EXISTS fb_events (mid TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now())")


def _send(psid: str, **body):
    r = httpx.post(GRAPH, params={"access_token": PAGE_TOKEN}, json={"recipient": {"id": psid}, **body}, timeout=20)
    if r.status_code >= 400:
        print(f"[messenger] send failed {r.status_code}: {r.text[:300]}", flush=True)


def _chunks(text: str, n: int = 1900):
    """Messenger нэг мессеж ≤2000 тэмдэгт."""
    while text:
        if len(text) <= n:
            yield text
            return
        cut = max(text.rfind("\n", 0, n), text.rfind(" ", 0, n))
        cut = cut if cut > n // 2 else n
        yield text[:cut].rstrip()
        text = text[cut:].lstrip()


def handle(psid: str, text: str):
    session_id = f"fb-{psid}"[:64]
    db.run("INSERT INTO chat_messages (session_id, role, content) VALUES (%s,'user',%s)", (session_id, text))
    _send(psid, sender_action="typing_on")
    out = agents.call("chat", {"sessionId": session_id, "chatInput": text})
    reply = out.get("output") or out.get("text") or FALLBACK
    db.run("INSERT INTO chat_messages (session_id, role, content) VALUES (%s,'assistant',%s)", (session_id, reply))
    for part in _chunks(reply):
        _send(psid, messaging_type="RESPONSE", message={"text": part})


@router.get("/webhooks/messenger")
def verify(request: Request):
    """Meta webhook-ийг бүртгэх үед нэг удаа дуудна."""
    q = request.query_params
    if VERIFY_TOKEN and q.get("hub.mode") == "subscribe" and hmac.compare_digest(q.get("hub.verify_token", ""), VERIFY_TOKEN):
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403)


@router.post("/webhooks/messenger")
async def receive(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if APP_SECRET:
        sig = request.headers.get("x-hub-signature-256", "")
        good = "sha256=" + hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, good):
            raise HTTPException(403)
    if not PAGE_TOKEN:
        return {"ok": True, "note": "FB_PAGE_TOKEN тохируулаагүй"}
    try:
        body = json.loads(raw)
    except ValueError:
        raise HTTPException(400)
    if body.get("object") != "page":
        return {"ok": True}
    for entry in body.get("entry", []):
        for ev in entry.get("messaging", []):
            msg = ev.get("message") or {}
            psid = (ev.get("sender") or {}).get("id")
            text = (msg.get("text") or (ev.get("postback") or {}).get("title") or "").strip()[:1000]
            if not psid or not text or msg.get("is_echo"):
                continue
            mid = msg.get("mid") or f"{psid}:{ev.get('timestamp')}"
            if not db.one("INSERT INTO fb_events (mid) VALUES (%s) ON CONFLICT DO NOTHING RETURNING mid", (mid,)):
                continue  # давтагдсан хүргэлт
            background.add_task(handle, psid, text)  # Meta-д шууд 200 буцаана, хариуг ард нь илгээнэ
    return {"ok": True}
