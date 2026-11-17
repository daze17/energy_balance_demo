"""Админ самбар — брэндийн өнгөтэй, нэвтрэх хуудастай."""
import bcrypt
from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import RedirectResponse

from . import agents, db

router = APIRouter(prefix="/admin")

BOOKING_STATUSES = ["Шинэ", "Илгээсэн", "Батлагдсан", "Татгалзсан"]


def render(request: Request, tpl: str, **ctx):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/admin/login", status_code=303)
    ctx.update(user=user, active=tpl.split("/")[-1].replace(".html", ""),
               new_count=db.one("SELECT count(*) AS n FROM bookings WHERE status='Шинэ'")["n"],
               pending_posts=db.one("SELECT count(*) AS n FROM posts WHERE status='Хүлээгдэж буй'")["n"])
    return request.app.state.templates.TemplateResponse(request, tpl, ctx)


def authed(request: Request) -> bool:
    return bool(request.session.get("user"))


def back(url: str):
    return RedirectResponse(url, status_code=303)


# ---------- Нэвтрэх ----------

@router.get("/login")
def login_page(request: Request, error: str | None = None):
    return request.app.state.templates.TemplateResponse(request, "admin/login.html", {"error": error})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    u = db.one("SELECT * FROM admin_users WHERE email=%s", (email.strip().lower(),))
    if not u or not bcrypt.checkpw(password.encode(), u["password_hash"].encode()):
        return back("/admin/login?error=1")
    request.session["user"] = {"email": u["email"], "name": u["name"]}
    return back("/admin")


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return back("/admin/login")


# ---------- Хянах самбар ----------

@router.get("")
def dashboard(request: Request):
    if not authed(request):
        return back("/admin/login")
    k = db.one("""
      SELECT
        (SELECT count(*) FROM bookings) AS bookings,
        (SELECT count(*) FROM bookings WHERE status='Шинэ') AS new_bookings,
        (SELECT count(*) FROM agent_runs WHERE status='success' AND agent IN ('booking','energy')) AS emails,
        (SELECT count(*) FROM agent_runs WHERE status='success' AND agent='chat') AS answers,
        (SELECT count(*) FROM posts WHERE source='ai') AS ai_posts,
        (SELECT count(*) FROM energy_reports) AS reports,
        (SELECT count(*) FROM agent_runs) AS runs,
        (SELECT count(*) FROM agent_runs WHERE status='success') AS ok_runs,
        (SELECT coalesce(round(avg(duration_ms)/1000.0,1),0) FROM agent_runs WHERE status='success') AS avg_sec
    """)
    saved_min = sum(
        r["n"] * agents.AGENTS[r["agent"]]["minutes_saved"]
        for r in db.all("SELECT agent, count(*) AS n FROM agent_runs WHERE status='success' GROUP BY agent")
        if r["agent"] in agents.AGENTS
    )
    per_agent = {r["agent"]: r for r in db.all(
        "SELECT agent, count(*) AS n, count(*) FILTER (WHERE status='success') AS ok, "
        "round(avg(duration_ms) FILTER (WHERE status='success')/1000.0,1) AS avg_sec FROM agent_runs GROUP BY agent")}
    daily = db.all("""
      SELECT d::date AS day, count(b.id) AS n
      FROM generate_series(current_date - 13, current_date, interval '1 day') d
      LEFT JOIN bookings b ON b.created_at::date = d::date
      GROUP BY d ORDER BY d""")
    by_service = db.all("""
      SELECT s.name, count(b.id) AS n FROM services s LEFT JOIN bookings b ON b.service_id=s.id
      GROUP BY s.id ORDER BY n DESC, s.sort_order""")
    runs = db.all("SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT 8")
    return render(request, "admin/dashboard.html", k=k, saved_hours=round(saved_min / 60, 1), per_agent=per_agent,
                  agent_meta=agents.AGENTS, daily=daily, max_daily=max([d["n"] for d in daily] + [1]),
                  by_service=by_service, max_service=max([s["n"] for s in by_service] + [1]), runs=runs)


# ---------- Захиалга ----------

@router.get("/bookings")
def bookings(request: Request, status: str | None = None):
    if not authed(request):
        return back("/admin/login")
    rows = db.all("""
      SELECT b.*, s.name AS service_name, st.name AS staff_name FROM bookings b
      LEFT JOIN services s ON s.id=b.service_id LEFT JOIN staff st ON st.id=b.assigned_staff_id
      WHERE (%(st)s::text IS NULL OR b.status=%(st)s) ORDER BY b.created_at DESC""", {"st": status})
    staff = db.all("SELECT id, name FROM staff WHERE active ORDER BY id")
    return render(request, "admin/bookings.html", rows=rows, staff=staff, statuses=BOOKING_STATUSES, current=status)


@router.post("/bookings/{bid}/status")
def booking_status(request: Request, bid: int, status: str = Form(...), staff_id: str = Form("")):
    if authed(request) and status in BOOKING_STATUSES:
        db.run("UPDATE bookings SET status=%s, assigned_staff_id=coalesce(%s, assigned_staff_id) WHERE id=%s",
               (status, int(staff_id) if staff_id else None, bid))
    return back(request.headers.get("referer") or "/admin/bookings")


@router.post("/bookings/{bid}/resend")
def booking_resend(request: Request, bid: int, background: BackgroundTasks):
    if authed(request):
        from .main import run_booking_agent
        background.add_task(run_booking_agent, bid)
    return back("/admin/bookings")


# ---------- Үйлчилгээ (CRUD) ----------

@router.get("/services")
def services(request: Request, edit: int | None = None):
    if not authed(request):
        return back("/admin/login")
    rows = db.all("SELECT * FROM services ORDER BY sort_order, id")
    item = db.one("SELECT * FROM services WHERE id=%s", (edit,)) if edit else None
    return render(request, "admin/services.html", rows=rows, item=item)


@router.post("/services")
def services_save(request: Request, id: str = Form(""), name: str = Form(...), short_desc: str = Form(...),
                  description: str = Form(...), price_from: str = Form(""), price_note: str = Form(""),
                  duration: str = Form(""), sort_order: int = Form(0), active: str = Form("")):
    if not authed(request):
        return back("/admin/login")
    vals = (name, short_desc, description, int(price_from) if price_from.strip() else None,
            price_note or None, duration or None, sort_order, bool(active))
    if id:
        db.run("""UPDATE services SET name=%s, short_desc=%s, description=%s, price_from=%s, price_note=%s,
                  duration=%s, sort_order=%s, active=%s WHERE id=%s""", (*vals, int(id)))
    else:
        db.run("""INSERT INTO services (name, short_desc, description, price_from, price_note, duration, sort_order, active)
                  VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", vals)
    return back("/admin/services")


@router.post("/services/{sid}/delete")
def services_delete(request: Request, sid: int):
    if authed(request):
        db.run("UPDATE services SET active=false WHERE id=%s", (sid,))
    return back("/admin/services")


# ---------- Ажилтан (CRUD) ----------

@router.get("/staff")
def staff(request: Request, edit: int | None = None):
    if not authed(request):
        return back("/admin/login")
    rows = db.all("""SELECT st.*, (SELECT count(*) FROM bookings b WHERE b.assigned_staff_id=st.id) AS jobs
                     FROM staff st ORDER BY active DESC, id""")
    item = db.one("SELECT * FROM staff WHERE id=%s", (edit,)) if edit else None
    return render(request, "admin/staff.html", rows=rows, item=item)


@router.post("/staff")
def staff_save(request: Request, id: str = Form(""), name: str = Form(...), role: str = Form(...),
               email: str = Form(""), phone: str = Form(""), active: str = Form("")):
    if not authed(request):
        return back("/admin/login")
    if id:
        db.run("UPDATE staff SET name=%s, role=%s, email=%s, phone=%s, active=%s WHERE id=%s",
               (name, role, email or None, phone or None, bool(active), int(id)))
    else:
        db.run("INSERT INTO staff (name, role, email, phone, active) VALUES (%s,%s,%s,%s,true)",
               (name, role, email or None, phone or None))
    return back("/admin/staff")


@router.post("/staff/{sid}/delete")
def staff_delete(request: Request, sid: int):
    if authed(request):
        db.run("UPDATE staff SET active=false WHERE id=%s", (sid,))
    return back("/admin/staff")


# ---------- Контент (Агент 3) + Facebook ----------

@router.get("/content")
def content(request: Request, error: str | None = None):
    if not authed(request):
        return back("/admin/login")
    rows = db.all("SELECT * FROM posts ORDER BY (status='Хүлээгдэж буй') DESC, created_at DESC")
    return render(request, "admin/content.html", rows=rows, error=error)


@router.post("/content/generate")
def content_generate(request: Request, topic: str = Form("")):
    if not authed(request):
        return back("/admin/login")
    out = agents.call("content", {"topic": topic.strip()}, timeout=180)
    if out.get("error"):
        return back("/admin/content?error=1")
    return back("/admin/content")


@router.post("/posts/{pid}/status")
def post_status(request: Request, pid: int, status: str = Form(...), caption: str = Form(None)):
    if authed(request) and status in ("Нийтэлсэн", "Татгалзсан", "Хүлээгдэж буй"):
        if caption is not None:
            db.run("UPDATE posts SET caption=%s WHERE id=%s", (caption, pid))
        db.run("""UPDATE posts SET status=%s,
                  published_at = CASE WHEN %s='Нийтэлсэн' THEN now() ELSE published_at END WHERE id=%s""",
               (status, status, pid))
    return back("/admin/facebook" if status == "Нийтэлсэн" else "/admin/content")


@router.get("/facebook")
def facebook(request: Request):
    if not authed(request):
        return back("/admin/login")
    rows = db.all("SELECT * FROM posts WHERE status='Нийтэлсэн' ORDER BY published_at DESC")
    return render(request, "admin/facebook.html", rows=rows)


# ---------- Чат (Агент 2) ----------

@router.get("/chat")
def chat(request: Request, s: str | None = None):
    if not authed(request):
        return back("/admin/login")
    sessions = db.all("""SELECT session_id, min(created_at) AS started, max(created_at) AS last, count(*) AS n,
                         (array_agg(content ORDER BY created_at) FILTER (WHERE role='user'))[1] AS first_q
                         FROM chat_messages GROUP BY session_id ORDER BY last DESC""")
    sel = s or (sessions[0]["session_id"] if sessions else None)
    msgs = db.all("SELECT * FROM chat_messages WHERE session_id=%s ORDER BY created_at, id", (sel,)) if sel else []
    return render(request, "admin/chat.html", sessions=sessions, sel=sel, msgs=msgs)


# ---------- Эрчим хүчний тайлан (Агент 4) ----------

@router.get("/energy")
def energy(request: Request, r: int | None = None):
    if not authed(request):
        return back("/admin/login")
    rows = db.all("SELECT * FROM energy_reports ORDER BY created_at DESC")
    sel = db.one("SELECT * FROM energy_reports WHERE id=%s", (r,)) if r else (rows[0] if rows else None)
    return render(request, "admin/energy.html", rows=rows, sel=sel)


# ---------- Агентууд ----------

@router.get("/agents")
def agents_page(request: Request):
    if not authed(request):
        return back("/admin/login")
    runs = db.all("SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT 50")
    stats = {r["agent"]: r for r in db.all(
        "SELECT agent, count(*) AS n, count(*) FILTER (WHERE status='success') AS ok, max(started_at) AS last "
        "FROM agent_runs GROUP BY agent")}
    return render(request, "admin/agents.html", runs=runs, stats=stats, meta=agents.AGENTS)


@router.get("/brand")
def brand(request: Request):
    if not authed(request):
        return back("/admin/login")
    return render(request, "admin/brand.html")
