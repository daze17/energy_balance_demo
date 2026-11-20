"""Энержи Баланс — нүүр хуудас + админ самбар (FastAPI)."""
import os
import uuid
from datetime import date
from pathlib import Path

import bcrypt
import markdown as md
from fastapi import BackgroundTasks, FastAPI, Form, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from . import agents, db, messenger
from .admin import router as admin_router

BASE = Path(__file__).parent
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "local-internal-token")

app = FastAPI(title="Энержи Баланс")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev"), max_age=60 * 60 * 12)
# Чат виджетийг өөр домэйн (жишээ нь energybalance.mn) дээр суулгахад хэрэгтэй
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CHAT_ALLOWED_ORIGINS", "*").split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.mount("/brand", StaticFiles(directory="/app/brand"), name="brand")

templates = Jinja2Templates(directory=BASE / "templates")


def money(v):
    if v is None:
        return "Тохиролцоно"
    if v == 0:
        return "Үнэгүй"
    return f"{int(v):,}".replace(",", "'") + "₮"


templates.env.filters["money"] = money
templates.env.filters["md"] = lambda t: md.markdown(t or "", extensions=["nl2br"])
# Админ «Агентууд» хуудасны холбоосууд (сервер дээр .env-ээр өөрчилнө)
templates.env.globals["N8N_PUBLIC_URL"] = os.environ.get("N8N_PUBLIC_URL", "http://localhost:47678")
templates.env.globals["MAILBOX_URL"] = os.environ.get("MAILBOX_URL", "http://localhost:47825")
templates.env.globals["COMPANY"] = {
    "name": "Энержи Баланс ХХК",
    "slogan": "Эрчим хүчний зохистой хэрэглээ — Бизнесийн амжилт",
    "phone": "+976 8811 3855",
    "email": "energybalance.mgl@gmail.com",
    "address": "ХУД 8-р хороо, Нүхт 247",
}
app.state.templates = templates
app.include_router(admin_router)
app.include_router(messenger.router)


@app.on_event("startup")
def ensure_admin():
    db.init_schema(os.environ.get("DB_INIT_DIR", "/app/db_init"))
    messenger.init()
    db.run("ALTER TABLE posts ADD COLUMN IF NOT EXISTS fb_post_id TEXT")  # хуучин өгөгдлийн санд багана нэмнэ
    email = os.environ.get("ADMIN_EMAIL", "admin@energybalance.local")
    pw = os.environ.get("ADMIN_PASSWORD", "EnergyBalance2026")
    if not db.one("SELECT id FROM admin_users WHERE email=%s", (email,)):
        h = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        db.run("INSERT INTO admin_users (email, name, password_hash) VALUES (%s,%s,%s) ON CONFLICT (email) DO NOTHING",
               (email, "Админ", h))


# ---------- Агент 1: захиалга баталгаажуулах ----------

def booking_payload(booking_id: int) -> dict:
    b = db.one(
        """SELECT b.*, s.name AS service_name, s.description AS service_desc, s.price_from, s.price_note, s.duration
           FROM bookings b LEFT JOIN services s ON s.id=b.service_id WHERE b.id=%s""",
        (booking_id,),
    )
    return {
        "booking_id": b["id"],
        "name": b["name"],
        "email": b["email"],
        "phone": b["phone"] or "",
        "company": b["company"] or "",
        "building_type": b["building_type"] or "",
        "message": b["message"] or "",
        "preferred_date": b["preferred_date"].isoformat() if b["preferred_date"] else "",
        "service_name": b["service_name"] or "Ерөнхий зөвлөгөө",
        "service_desc": b["service_desc"] or "",
        "service_price": money(b["price_from"]) + (f" ({b['price_note']})" if b["price_note"] else ""),
        "service_duration": b["duration"] or "",
        "source": b["source"],
    }


def run_booking_agent(booking_id: int):
    agents.call("booking", booking_payload(booking_id))


def create_booking(data: dict, source: str) -> int:
    row = db.one(
        """INSERT INTO bookings (name, phone, email, company, service_id, building_type, message, preferred_date, source)
           VALUES (%(name)s,%(phone)s,%(email)s,%(company)s,%(service_id)s,%(building_type)s,%(message)s,%(preferred_date)s,%(source)s)
           RETURNING id""",
        {**data, "source": source},
    )
    return row["id"]


# ---------- Нүүр хуудас ----------

@app.get("/")
def landing(request: Request, booked: int | None = None):
    services = db.all("SELECT * FROM services WHERE active ORDER BY sort_order, id")
    projects = db.all("SELECT * FROM projects ORDER BY year DESC, id DESC")
    return templates.TemplateResponse(
        request, "landing.html",
        {"services": services, "projects": projects, "booked": booked, "today": date.today().isoformat()},
    )


@app.post("/book")
def book(
    background: BackgroundTasks,
    name: str = Form(...), email: str = Form(...), phone: str = Form(""),
    company: str = Form(""), service_id: int | None = Form(None), building_type: str = Form(""),
    message: str = Form(""), preferred_date: str = Form(""),
):
    bid = create_booking(
        {"name": name.strip(), "email": email.strip(), "phone": phone.strip(), "company": company.strip() or None,
         "service_id": service_id, "building_type": building_type or None, "message": message.strip() or None,
         "preferred_date": preferred_date or None},
        "web",
    )
    background.add_task(run_booking_agent, bid)
    return RedirectResponse(f"/?booked={bid}#book", status_code=303)


# ---------- Агент 2: чат ----------

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    session_id = (body.get("session_id") or str(uuid.uuid4()))[:64]
    text = (body.get("message") or "").strip()[:1000]
    if not text:
        raise HTTPException(400, "empty")
    db.run("INSERT INTO chat_messages (session_id, role, content) VALUES (%s,'user',%s)", (session_id, text))
    # Thread-д ажиллуулна: n8n чат агент create_booking хийхдээ энэ серверийг буцаж дууддаг
    out = await run_in_threadpool(agents.call, "chat", {"sessionId": session_id, "chatInput": text})
    reply = out.get("output") or out.get("text") or (
        "Уучлаарай, түр алдаа гарлаа. Та +976 8811 3855 дугаарт залгана уу." if out.get("error") else "…")
    db.run("INSERT INTO chat_messages (session_id, role, content) VALUES (%s,'assistant',%s)", (session_id, reply))
    return {"session_id": session_id, "reply": reply}


@app.get("/api/chat/history")
def chat_history(session_id: str = ""):
    """Виджет дахин нээгдэхэд өмнөх яриаг сэргээнэ (session_id = таамаглахад хэцүү UUID)."""
    if len(session_id) < 16:
        return {"messages": []}
    rows = db.all(
        "SELECT role, content, created_at FROM chat_messages WHERE session_id=%s ORDER BY created_at, id LIMIT 100",
        (session_id[:64],),
    )
    return {"messages": [{**r, "created_at": r["created_at"].isoformat()} for r in rows]}


# ---------- Агент 4: эрчим хүчний шинжилгээ ----------

@app.post("/api/energy")
async def energy(request: Request):
    b = await request.json()
    try:
        payload = {
            "client_name": str(b["client_name"]).strip()[:120],
            "email": str(b.get("email", "")).strip()[:120],
            "company": str(b.get("company", "")).strip()[:120],
            "building_type": str(b.get("building_type", "Оффис"))[:60],
            "area_m2": float(b["area_m2"]),
            "elec_kwh_year": float(b["elec_kwh_year"]),
            "heat_gcal_year": float(b.get("heat_gcal_year") or 0),
            "elec_cost_year": float(b["elec_cost_year"]) if b.get("elec_cost_year") else None,
            "heat_cost_year": float(b["heat_cost_year"]) if b.get("heat_cost_year") else None,
        }
    except (KeyError, ValueError, TypeError):
        raise HTTPException(400, "Талбаруудаа зөв бөглөнө үү")
    if payload["area_m2"] <= 0:
        raise HTTPException(400, "Талбай 0-ээс их байх ёстой")
    out = await run_in_threadpool(agents.call, "energy", payload, timeout=180)
    if out.get("error"):
        return JSONResponse({"error": "Агент түр ажиллахгүй байна. Дахин оролдоно уу."}, status_code=502)
    out["recommendations_html"] = md.markdown(out.get("recommendations", ""), extensions=["nl2br"])
    return out


# ---------- n8n чат агентаас дуудагддаг дотоод API ----------

@app.post("/api/internal/booking")
async def internal_booking(request: Request, background: BackgroundTasks, x_internal_token: str = Header("")):
    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(401)
    b = await request.json()
    svc = None
    if b.get("service_name"):
        svc = db.one("SELECT id FROM services WHERE name ILIKE %s ORDER BY sort_order LIMIT 1", (f"%{b['service_name'][:40]}%",))
    if not b.get("name") or not (b.get("email") or b.get("phone")):
        return {"ok": False, "error": "Нэр болон и-мэйл эсвэл утас шаардлагатай"}
    bid = create_booking(
        {"name": b["name"], "email": b.get("email") or None, "phone": b.get("phone") or None,
         "company": b.get("company") or None, "service_id": svc["id"] if svc else 1,
         "building_type": b.get("building_type") or None, "message": b.get("message") or None,
         "preferred_date": b.get("preferred_date") or None},
        "chat",
    )
    if b.get("email"):
        background.add_task(run_booking_agent, bid)
    return {"ok": True, "booking_id": bid, "message": f"Захиалга #{bid} бүртгэгдлээ. Баталгаажуулах и-мэйл илгээгдэнэ."}


@app.get("/healthz")
def healthz():
    db.one("SELECT 1")
    return {"ok": True}
