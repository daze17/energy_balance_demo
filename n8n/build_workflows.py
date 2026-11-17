#!/usr/bin/env python3
"""4 AI агентын n8n workflow JSON-г үүсгэнэ → n8n/workflows/*.json

Prompt, node-уудыг энд засаад `python3 n8n/build_workflows.py` ажиллуулж,
дараа нь `docker compose up -d n8n-init n8n` хийхэд n8n руу дахин импортлогдоно.
`__PLACEHOLDER__` утгуудыг init.sh .env-ээс орлуулна.
"""
import json
import uuid
from pathlib import Path

OUT = Path(__file__).parent / "workflows"
NS = uuid.UUID("6f1c5c1e-0e1b-4b7a-9a52-eb0000000000")

PG = {"postgres": {"id": "ebPostgres000001", "name": "Energy Balance DB"}}
SMTP = {"smtp": {"id": "ebSmtpMailpit001", "name": "Mailpit SMTP (Gmail-ийн орлуулагч)"}}
ANTH = {"anthropicApi": {"id": "ebAnthropic00001", "name": "Anthropic (Claude)"}}
HOOK_AUTH = {"httpHeaderAuth": {"id": "ebHookAuth000001", "name": "Webhook token (X-Internal-Token)"}}
FROM = "Energy Balance <__MAIL_FROM__>"

VOICE = """Чи «Энержи Баланс ХХК» (Energy Balance, energybalance.mn)-ийн нэрийн өмнөөс бичнэ — Улаанбаатарт байрладаг эрчим хүчний аудит, барилгын эрчим хүчний гэрчилгээжүүлэлт, ISO 50001 зөвлөх үйлчилгээ үзүүлдэг компани.
Уриа: «Эрчим хүчний зохистой хэрэглээ — Бизнесийн амжилт.»
Брэндийн дуу хоолой (Brand Book V1): санаа тавьдаг инженер шиг ярина — тайван, нарийн, тустай. Айдас төрүүлэхгүй, хэт сурталчлахгүй.
- Тодорхой: богино өгүүлбэр, нэг санаа. Мэргэжлийн үгийг тайлбаргүй хэрэглэхгүй.
- Нотолгоотой: тоо, хэмжилтэд тулгуурла. Таамаг тоо зохиохгүй; нарийн тоог аудитаар тодорхойлно гэж хэл.
- Бүтээлч: алдагдлыг нэрлээд, шийдэл ба нөхөх хугацааг хэл.
- Анхаарлын тэмдэг (!) болон эможи хэрэглэхгүй. «энерги» биш «эрчим хүч», «эко» биш «байгальд ээлтэй», «асар их хэмнэлт» биш «10–30% хэмнэлт» гэж бич.
Компанийн баримт: эхний жилд эрчим хүчний зардал 10–30% буурдаг; хөрөнгө оруулалт дунджаар 18–36 сард нөхөгддөг; хүлэмжийн хийн ялгарал 10–30% буурдаг; Эрчим Хүчний Зохицуулах Хорооны үнэлгээ 92.3% (2025); үйлчлүүлэгчийн сэтгэл ханамж 9.5/10. Үнэгүй 30 минутын анхан шатны зөвлөгөө өгдөг.
Холбоо барих: +976 8811 3855 · energybalance.mgl@gmail.com · ХУД 8-р хороо, Нүхт 247 · energybalance.mn"""


def nid(wf, name):
    return str(uuid.uuid5(NS, f"{wf}:{name}"))


def node(wf, name, type_, version, pos, params, creds=None, **extra):
    n = {"id": nid(wf, name), "name": name, "type": type_, "typeVersion": version, "position": pos, "parameters": params}
    if creds:
        n["credentials"] = creds
    n.update(extra)
    return n


def webhook(wf, path, pos=(0, 300), mode="lastNode"):
    # Header auth: n8n гаднаас нээлттэй байсан ч зөвхөн X-Internal-Token-тэй (вэб сервер) дуудна
    return node(wf, "Webhook", "n8n-nodes-base.webhook", 2.1, list(pos),
                {"httpMethod": "POST", "path": path, "responseMode": mode, "authentication": "headerAuth", "options": {}},
                HOOK_AUTH, webhookId=nid(wf, "webhook-id"))


GEMINI = {"googlePalmApi": {"id": "ebGemini00000001", "name": "Google Gemini"}}
PROVIDER = "gemini"  # main хэсэгт provider бүрээр солигдоно


def M():
    """Chat model node-ийн нэр (диаграм, n8n editor дээр харагдана)."""
    return "Gemini" if PROVIDER == "gemini" else "Claude"


def llm(wf, pos, max_tokens=1500):
    if PROVIDER == "gemini":
        # Gemini-ийн «thinking» токен maxOutputTokens-д тоологддог тул нөөцтэй өгнө
        return node(wf, M(), "@n8n/n8n-nodes-langchain.lmChatGoogleGemini", 1.2, list(pos),
                    {"modelName": "models/__GEMINI_MODEL__",
                     "options": {"maxOutputTokens": max_tokens + 6000, "temperature": 0.4}}, GEMINI)
    return node(wf, M(), "@n8n/n8n-nodes-langchain.lmChatAnthropic", 1.6, list(pos),
                {"model": {"__rl": True, "mode": "id", "value": "__CLAUDE_MODEL__"},
                 "options": {"maxTokensToSample": max_tokens}}, ANTH)


def chain(wf, name, pos, system, text):
    return node(wf, name, "@n8n/n8n-nodes-langchain.chainLlm", 1.9, list(pos), {
        "promptType": "define", "text": text,
        "messages": {"messageValues": [{"type": "SystemMessagePromptTemplate", "message": system}]},
    })


def code(wf, name, pos, js):
    return node(wf, name, "n8n-nodes-base.code", 2, list(pos), {"jsCode": js})


def pg(wf, name, pos, query, params=None):
    p = {"operation": "executeQuery", "query": query, "options": {}}
    if params:
        # Утга бүрийг [ ] массивт хийнэ — Postgres node (<2.8) таслалаар хуваахгүй, AI текст бүтнээрээ орно
        p["options"]["queryReplacement"] = "=" + ",".join("{{ [ " + x + " ] }}" for x in params)
    return node(wf, name, "n8n-nodes-base.postgres", 2.6, list(pos), p, PG)


def email(wf, name, pos, to, subject, text, html):
    return node(wf, name, "n8n-nodes-base.emailSend", 2.1, list(pos), {
        "fromEmail": FROM, "toEmail": to, "subject": subject, "emailFormat": "both",
        "text": text, "html": html, "options": {"appendAttribution": False},
    }, SMTP)


def main_conn(*names):
    c = {}
    for a, b in zip(names, names[1:]):
        c.setdefault(a, {"main": [[]]})["main"][0].append({"node": b, "type": "main", "index": 0})
    return c


def sub(conn, src, dst, kind):
    conn.setdefault(src, {}).setdefault(kind, [[]])[0].append({"node": dst, "type": kind, "index": 0})


def workflow(wid, name, nodes, connections, tags=()):
    return {"id": wid, "name": name, "active": True, "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1", "saveManualExecutions": True}, "pinData": {},
            "meta": {"templateCredsSetupCompleted": True}}


# HTML и-мэйлийн брэнд загвар (Brand Book 09 — и-мэйлийн гарын үсэг)
EMAIL_HTML_JS = r"""
const esc = s => String(s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function brandEmail(title, bodyHtml) {
  return `<div style="background:#F4F7F4;padding:24px 0;font-family:Inter,Arial,sans-serif;color:#183A27">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #E1E8E2">
    <div style="background:#1F5E3B;padding:18px 24px;color:#fff;letter-spacing:4px;font-size:13px">ENERGY BALANCE</div>
    <div style="padding:24px;font-size:15px;line-height:1.6">
      <div style="color:#3A8F5C;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px">${esc(title)}</div>
      ${bodyHtml}
    </div>
    <div style="border-top:3px solid #8DC149;padding:16px 24px;font-size:12px;color:#3A8F5C">
      Энержи Баланс ХХК · +976 8811 3855 · energybalance.mn<br>Эрчим хүчний зохистой хэрэглээ — Бизнесийн амжилт.
    </div>
  </div></div>`;
}
const textToHtml = t => esc(t).split(/\n{2,}/).map(p => `<p style="margin:0 0 12px">${p.replace(/\n/g,'<br>')}</p>`).join('');
"""

# ---------------------------------------------------------------- 1. Захиалга
def wf_booking():
    w = "booking"
    sys = VOICE + """

Даалгавар: вэб сайтаар ирсэн захиалгыг баталгаажуулах и-мэйлийн ИХ БИЕИЙГ бичнэ (гарчиг биш).
Шаардлага:
- 110–170 үг, энгийн текст. Markdown (**, #) хэрэглэхгүй. Жагсаалтад «— » тэмдэг ашигла.
- Бүтэц: 1) Нэрээр нь мэндлэх. 2) Захиалгыг хүлээн авснаа батлах: үйлчилгээ, хүссэн өдөр. 3) Тухайн хүний барилгын төрөл, мессежид тохирсон 1–2 өгүүлбэр: юуг шалгах, ямар үр дүн хүлээх (компанийн баримт тоог ашиглаж болно). 4) Дараагийн алхам: менежер 1 ажлын өдөрт холбогдож цагийг баталгаажуулна. 5) Уулзалтад бэлдэх 2–3 зүйл жагсаалтаар (жишээ нь сүүлийн 12 сарын цахилгаан, дулааны төлбөрийн баримт, барилгын талбай, зураг төсөл). 6) Гарын үсэг яг ингэж: «Хүндэтгэсэн,\nEnergy Balance баг\n+976 8811 3855 · energybalance.mn»
- Үнийг зөвхөн өгөгдсөн мэдээллээр дурд, шинээр зохиохгүй."""
    text = """=Захиалгын мэдээлэл:
Дугаар: #{{ $json.body.booking_id }}
Нэр: {{ $json.body.name }}
Байгууллага: {{ $json.body.company || '—' }}
Үйлчилгээ: {{ $json.body.service_name }}
Үйлчилгээний тайлбар: {{ $json.body.service_desc }}
Үнэ: {{ $json.body.service_price }}
Хугацаа: {{ $json.body.service_duration }}
Барилгын төрөл: {{ $json.body.building_type || '—' }}
Хүссэн өдөр: {{ $json.body.preferred_date || 'тодорхойгүй' }}
Харилцагчийн мессеж: {{ $json.body.message || '—' }}
Эх сурвалж: {{ $json.body.source === 'chat' ? 'вэб чат агент' : 'вэб сайтын форм' }}"""
    prep = EMAIL_HTML_JS + r"""
const b = $('Webhook').first().json.body;
const text = ($input.first().json.text || '').trim();
const subject = `Захиалга #${b.booking_id} хүлээн авлаа — ${b.service_name}`;
const facts = `<table style="width:100%;border-collapse:collapse;margin:4px 0 16px;font-size:14px">
  <tr><td style="padding:6px 0;color:#3A8F5C">Захиалга</td><td style="padding:6px 0"><b>#${esc(b.booking_id)}</b></td></tr>
  <tr><td style="padding:6px 0;color:#3A8F5C">Үйлчилгээ</td><td style="padding:6px 0">${esc(b.service_name)}</td></tr>
  <tr><td style="padding:6px 0;color:#3A8F5C">Хүссэн өдөр</td><td style="padding:6px 0">${esc(b.preferred_date || 'тохиролцоно')}</td></tr></table>`;
return [{ json: { to: b.email, subject, text, booking_id: b.booking_id,
  html: brandEmail('Захиалгын баталгаажуулалт', facts + textToHtml(text)) } }];
"""
    nodes = [
        webhook(w, "eb-booking"),
        chain(w, "AI: и-мэйл бичих", (260, 300), sys, text),
        llm(w, (260, 520), 900),
        code(w, "И-мэйл бэлдэх", (560, 300), prep),
        email(w, "И-мэйл илгээх (SMTP)", (780, 300), "={{ $json.to }}", "={{ $json.subject }}", "={{ $json.text }}", "={{ $json.html }}"),
        pg(w, "Төлөв шинэчлэх", (1000, 300),
           "UPDATE bookings SET status = CASE WHEN status = 'Шинэ' THEN 'Илгээсэн' ELSE status END, "
           "confirmation_email = $1, confirmed_at = now() WHERE id = $2 RETURNING id, status",
           ["$('И-мэйл бэлдэх').item.json.text", "$('И-мэйл бэлдэх').item.json.booking_id"]),
        code(w, "Хариу", (1220, 300),
             "const e = $('И-мэйл бэлдэх').first().json;\n"
             "return [{ json: { ok: true, booking_id: e.booking_id, status: $input.first().json.status, to: e.to, subject: e.subject, email: e.text } }];"),
    ]
    conn = main_conn("Webhook", "AI: и-мэйл бичих", "И-мэйл бэлдэх", "И-мэйл илгээх (SMTP)", "Төлөв шинэчлэх", "Хариу")
    sub(conn, M(), "AI: и-мэйл бичих", "ai_languageModel")
    return workflow("ebAgent1Booking0", "Агент 1 · Захиалга баталгаажуулах", nodes, conn)


# ---------------------------------------------------------------- 2. Чат
def wf_chat():
    w = "chat"
    sys = "=" + VOICE + """

Чиний үүрэг: energybalance.mn вэб сайтын чат дахь AI зөвлөх. Өнөөдөр: {{ $now.toFormat('yyyy-MM-dd') }}.
Дүрэм:
- Хариулт 2–5 өгүүлбэр, энгийн текст. Markdown (**, #) хэрэглэхгүй. Монголоор хариул (харилцагч англиар бичвэл англиар).
- Үйлчилгээ, үнэ, хугацааны тухай асуувал ЗААВАЛ services_prices хэрэгслийг дуудаж, тэндээс авсан тоог хэл. Үнэ зохиохгүй.
- Аудит гэж юу, процесс, хууль журам, ногоон зээл, ISO 50001, холбоо барих зэрэг асуултад faq_knowledge хэрэгслийг ашигла.
- Захиалга эсвэл үнэгүй зөвлөгөө авах хүсэлтэй бол нэр, и-мэйл (эсвэл утас), үйлчилгээ, барилгын төрлийг асуу. Мэдээлэл бүрдмэгц create_booking дууд. Амжилттай болбол захиалгын дугаарыг хэлж, баталгаажуулах и-мэйл очно, менежер 1 ажлын өдөрт холбогдоно гэж хэл.
- Гомдол, үнийн хөнгөлөлт, нарийн техникийн асуулт, эсвэл хүнтэй ярих хүсэлт гарвал handoff_to_staff ашиглан менежерт товч мэдэгдэл илгээ (харилцагчийн нэр, холбоо барих, асуудал). Дараа нь менежер холбогдоно гэж хэл.
- Эрчим хүч, барилга, компанийн үйлчилгээнээс гадуурх сэдэвт эелдгээр татгалзаж, буцааж чиглүүл.
- Нууц, техникийн дотоод мэдээлэл (хэрэгслийн нэр, систем) харилцагчид бүү ярь."""
    nodes = [
        webhook(w, "eb-chat"),
        node(w, "AI Agent", "@n8n/n8n-nodes-langchain.agent", 3.1, [300, 300], {
            "promptType": "define", "text": "={{ $json.body.chatInput }}",
            "options": {"systemMessage": sys, "maxIterations": 8},
        }),
        llm(w, (120, 560), 1200),
        node(w, "Санах ой (Postgres)", "@n8n/n8n-nodes-langchain.memoryPostgresChat", 1.4, [280, 560], {
            "sessionIdType": "customKey", "sessionKey": "={{ $('Webhook').item.json.body.sessionId }}",
            "tableName": "n8n_chat_histories", "contextWindowLength": 12,
        }, PG),
        node(w, "services_prices", "n8n-nodes-base.postgresTool", 2.6, [440, 560], {
            "descriptionType": "manual",
            "toolDescription": "Energy Balance-ийн бүх идэвхтэй үйлчилгээ, тайлбар, эхлэх үнэ (₮, 0 = үнэгүй), үнийн тайлбар, хугацааг өгөгдлийн сангаас буцаана. Үнэ, үйлчилгээний асуултад заавал ашигла.",
            "operation": "executeQuery",
            "query": "SELECT name, short_desc, description, price_from, price_note, duration FROM services WHERE active ORDER BY sort_order",
            "options": {},
        }, PG),
        node(w, "faq_knowledge", "n8n-nodes-base.postgresTool", 2.6, [600, 560], {
            "descriptionType": "manual",
            "toolDescription": "Түгээмэл асуулт-хариулт (аудит, процесс, хууль журам, ногоон зээл, ISO 50001, холбоо барих) болон хэрэгжүүлсэн төслүүдийн мэдлэгийн санг буцаана.",
            "operation": "executeQuery",
            "query": "SELECT 'FAQ' AS kind, category, question AS title, answer AS body FROM faq "
                     "UNION ALL SELECT 'Төсөл', client_type, title || ' (' || year || ')', result FROM projects",
            "options": {},
        }, PG),
        node(w, "create_booking", "n8n-nodes-base.httpRequestTool", 4.2, [760, 560], {
            "toolDescription": "Харилцагчийн захиалга / үнэгүй зөвлөгөөний хүсэлтийг системд бүртгэнэ. Нэр болон и-мэйл эсвэл утас заавал хэрэгтэй. Захиалгын дугаар буцаана.",
            "method": "POST", "url": "__WEB_INTERNAL_URL__/api/internal/booking",
            "sendHeaders": True, "specifyHeaders": "keypair",
            "headerParameters": {"parameters": [{"name": "X-Internal-Token", "value": "__INTERNAL_TOKEN__"}]},
            "sendBody": True, "contentType": "json", "specifyBody": "keypair",
            "bodyParameters": {"parameters": [
                {"name": "name", "value": "={{ $fromAI('name', 'Харилцагчийн нэр', 'string') }}"},
                {"name": "email", "value": "={{ $fromAI('email', 'И-мэйл хаяг, мэдэхгүй бол хоосон', 'string', '') }}"},
                {"name": "phone", "value": "={{ $fromAI('phone', 'Утасны дугаар, мэдэхгүй бол хоосон', 'string', '') }}"},
                {"name": "company", "value": "={{ $fromAI('company', 'Байгууллагын нэр, байхгүй бол хоосон', 'string', '') }}"},
                {"name": "service_name", "value": "={{ $fromAI('service_name', 'services_prices дахь үйлчилгээний нэр', 'string', 'Үнэгүй 30 минутын зөвлөгөө') }}"},
                {"name": "building_type", "value": "={{ $fromAI('building_type', 'Барилгын төрөл: Оффис, Үйлдвэр, Сургууль, Орон сууц гэх мэт', 'string', '') }}"},
                {"name": "preferred_date", "value": "={{ $fromAI('preferred_date', 'Уулзах өдөр YYYY-MM-DD, мэдэхгүй бол хоосон', 'string', '') }}"},
                {"name": "message", "value": "={{ $fromAI('message', 'Харилцагчийн хэрэгцээний товч тайлбар', 'string', '') }}"},
            ]},
            "options": {},
        }),
        node(w, "handoff_to_staff", "n8n-nodes-base.emailSendTool", 2.1, [920, 560], {
            "descriptionType": "manual",
            "toolDescription": "Менежерт и-мэйлээр мэдэгдэл илгээж, харилцагчийг хүнд шилжүүлнэ (гомдол, хөнгөлөлт, нарийн техникийн асуулт, хүнтэй ярих хүсэлт).",
            "fromEmail": FROM, "toEmail": "__STAFF_EMAIL__",
            "subject": "=[Чат → менежер] {{ $fromAI('subject', 'Товч гарчиг', 'string') }}",
            "emailFormat": "text",
            "text": "={{ $fromAI('body', 'Харилцагчийн нэр, холбоо барих мэдээлэл, асуудлын товч агуулга', 'string') }}\n\n— Энэ мэдэгдлийг вэб чат AI агент илгээв.",
            "options": {"appendAttribution": False},
        }, SMTP),
    ]
    conn = main_conn("Webhook", "AI Agent")
    sub(conn, M(), "AI Agent", "ai_languageModel")
    sub(conn, "Санах ой (Postgres)", "AI Agent", "ai_memory")
    for t in ("services_prices", "faq_knowledge", "create_booking", "handoff_to_staff"):
        sub(conn, t, "AI Agent", "ai_tool")
    return workflow("ebAgent2Chat0000", "Агент 2 · Харилцагчийн зөвлөх чат", nodes, conn)


# ---------------------------------------------------------------- 3. Контент
def wf_content():
    w = "content"
    sys = VOICE + """

Даалгавар: Facebook Page-д зориулсан нэг пост ба карусель слайдын зургийн prompt бэлдэнэ.
Brand Book-ийн сошиал дүрэм: нэг постонд нэг тоо эсвэл нэг санаа; бодит, хэмжигдэхүйц; бараан ба цайвар слайдыг ээлжлүүлнэ; лого зүүн дээд буланд.
Caption шаардлага: 60–120 үг, Монгол хэлээр. Эхний мөр — асуулт эсвэл нэг тоо. Дунд нь 2–4 богино догол мөр. Төгсгөлд «Үнэгүй 30 минутын зөвлөгөө: 8811 3855» гэх мэт уриалга. Сүүлийн мөрөнд 3 hashtag: #EnergyBalance болон сэдэвт тохирох 2. Эможи, анхаарлын тэмдэг хэрэглэхгүй.
Слайд: 3 эсвэл 4 ширхэг. prompt-ыг АНГЛИ хэлээр, зураг үүсгэх AI-д зориулж бич: flat vector illustration, calm, lots of white space, palette deep green #1F5E3B, green #3A8F5C, lime #8DC149, light grey #F4F7F4; бодит объект (барилга, хэмжилтийн багаж, цонх, үйлдвэр, нарны панел); утаа, неон, stock-photo хэв маяг хориглоно; слайд дээр гарах монгол гарчгийг prompt дотор "Headline text: '...'" гэж оруул.
ЗӨВХӨН дараах JSON-г буцаа, өөр текст бүү нэм:
{"caption": "...", "slides": [{"slide_number": 1, "prompt": "..."}]}"""
    pick = r"""
const TOPICS = [
  'Өвлийн улиралд барилгын дулаан алдагдал (цонх, хаалга, дээвэр)',
  'Барилгын эрчим хүчний гэрчилгээ ба банкны ногоон зээл',
  'ISO 50001 эрчим хүчний менежментийн тогтолцоо 6 сард',
  'Үйлдвэрийн уурын зуух, шахуургын үр ашиг',
  'LED гэрэлтүүлэг ба хөдөлгөөн мэдрэгчээр гэрэлтүүлгийн зардлыг бууруулах',
  'Тепловизор хэмжилт: дулаан алдагдлыг нүдээр харах',
  'Эрчим хүчний аудитын 5 үе шат',
  'Хөрөнгө оруулалт 18–36 сард нөхөгдөх хэмнэлтийн арга хэмжээ',
  'Оффисын агааржуулалт, халаалтын автомат удирдлага',
  'Эрчим хүч хэмнэлтийн тухай хууль: томоохон хэрэглэгчийн үүрэг',
];
const body = $input.first().json.body || {};
const topic = (body.topic || '').trim() || TOPICS[Math.floor(Math.random() * TOPICS.length)];
return [{ json: { topic, trigger: body.topic !== undefined ? 'admin' : 'schedule' } }];
"""
    parse = r"""
const raw = $input.first().json.text || '';
const m = raw.match(/\{[\s\S]*\}/);
if (!m) throw new Error('AI JSON буцаасангүй: ' + raw.slice(0, 200));
const data = JSON.parse(m[0]);
const slides = (data.slides || []).map((s, i) => ({ slide_number: s.slide_number || i + 1, prompt: String(s.prompt || '') }));
return [{ json: { topic: $('Сэдэв сонгох').first().json.topic, caption: String(data.caption || '').trim(), slides } }];
"""
    nodes = [
        webhook(w, "eb-content", (0, 220)),
        node(w, "Даваа/Лхагва/Баасан 09:00", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 420], {
            "rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * 1,3,5"}]}}),
        code(w, "Сэдэв сонгох", (240, 300), pick),
        chain(w, "AI: пост бичих", (460, 300), sys, "=Сэдэв: {{ $json.topic }}\nЭнэ сэдвээр Energy Balance-ийн Facebook пост бэлд."),
        llm(w, (460, 520), 1800),
        code(w, "JSON задлах", (760, 300), parse),
        pg(w, "Пост хадгалах (Хүлээгдэж буй)", (980, 300),
           "INSERT INTO posts (topic, caption, slides, status, source) VALUES ($1, $2, $3::jsonb, 'Хүлээгдэж буй', 'ai') "
           "RETURNING id, topic, caption, slides, status",
           ["$json.topic", "$json.caption", "JSON.stringify($json.slides)"]),
    ]
    conn = main_conn("Webhook", "Сэдэв сонгох", "AI: пост бичих", "JSON задлах", "Пост хадгалах (Хүлээгдэж буй)")
    conn["Даваа/Лхагва/Баасан 09:00"] = {"main": [[{"node": "Сэдэв сонгох", "type": "main", "index": 0}]]}
    sub(conn, M(), "AI: пост бичих", "ai_languageModel")
    return workflow("ebAgent3Content0", "Агент 3 · Контент (Facebook)", nodes, conn)


# ---------------------------------------------------------------- 4. Эрчим хүчний шинжилгээ
def wf_energy():
    w = "energy"
    calc = r"""
// Урьдчилсан эрчим хүчний баланс (жишиг коэффициент — нарийн дүнг аудитаар тодорхойлно)
const b = $input.first().json.body;
const num = v => (v === null || v === undefined || v === '' ? null : Number(v));
const area = num(b.area_m2), elec = num(b.elec_kwh_year) || 0, gcal = num(b.heat_gcal_year) || 0;
const GCAL_KWH = 1163;           // 1 Гкал = 1163 кВт·ц
const TARIFF_E = 230;            // ₮/кВт·ц (ААН-ийн дундаж, жишиг)
const TARIFF_H = 32000;          // ₮/Гкал (жишиг)
const EF_E = 0.95;               // кг CO₂/кВт·ц — Төвийн эрчим хүчний систем (нүүрс давамгайлсан)
const EF_H = 0.40;               // т CO₂/Гкал — ДЦС-ын дулаан
const BENCH = { 'Оффис': 260, 'Сургууль': 280, 'Цэцэрлэг': 300, 'Эмнэлэг': 380, 'Худалдааны төв': 330,
                'Орон сууц': 250, 'Зочид буудал': 340, 'Үйлдвэр': null };
const heat_kwh = gcal * GCAL_KWH;
const total_kwh = elec + heat_kwh;
const eui = total_kwh / area;
const elec_cost = num(b.elec_cost_year) ?? elec * TARIFF_E;
const heat_cost = num(b.heat_cost_year) ?? gcal * TARIFF_H;
const total_cost = elec_cost + heat_cost;
const co2_t = elec * EF_E / 1000 + gcal * EF_H;
const scale = [[100,'A','Маш сайн — шинэ, эрчим хүчний хэмнэлттэй барилгын түвшин'],[150,'B','Сайн'],[200,'C','Дунджаас сайн'],
  [250,'D','Дундаж'],[300,'E','Дунджаас муу — хэмнэлтийн боломж их'],[400,'F','Муу — дулаан алдагдал өндөр'],[Infinity,'G','Маш муу — яаралтай арга хэмжээ хэрэгтэй']];
const [, grade, grade_text] = scale.find(([lim]) => eui <= lim);
const bench = BENCH[b.building_type] ?? null;
const r = (v, d = 0) => Math.round(v * 10 ** d) / 10 ** d;
const metrics = {
  area_m2: area, elec_kwh: r(elec), heat_kwh: r(heat_kwh), total_kwh: r(total_kwh),
  heat_share_pct: r(heat_kwh / total_kwh * 100), elec_share_pct: r(elec / total_kwh * 100),
  eui_kwh_m2: r(eui), benchmark_kwh_m2: bench, vs_benchmark_pct: bench ? r((eui / bench - 1) * 100) : null,
  grade, grade_text, elec_cost: r(elec_cost), heat_cost: r(heat_cost), total_cost: r(total_cost),
  co2_t: r(co2_t, 1),
  saving_cost_low: r(total_cost * 0.10), saving_cost_mid: r(total_cost * 0.20), saving_cost_high: r(total_cost * 0.30),
  saving_kwh_mid: r(total_kwh * 0.20), saving_co2_mid: r(co2_t * 0.20, 1),
  assumptions: { gcal_to_kwh: GCAL_KWH, tariff_elec: TARIFF_E, tariff_heat: TARIFF_H, ef_elec: EF_E, ef_heat: EF_H },
};
return [{ json: { input: b, metrics } }];
"""
    sys = VOICE + """

Даалгавар: урьдчилсан эрчим хүчний балансын тооцоонд тулгуурлан харилцагчид зориулсан товч дүгнэлт, зөвлөмж бичнэ.
Формат — Markdown, 180–280 үг:
1. Эхэнд 2 өгүүлбэрийн дүгнэлт: кВт·ц/м²·жил, зэрэглэл, жишигтэй харьцуулалт (жишиг байвал), дулаан ба цахилгааны хувь.
2. «### Санал болгох арга хэмжээ» — барилгын төрөлд тохирсон 4 арга хэмжээ, дугаарласан жагсаалт. Тус бүрд: юу хийх, хүлээгдэх хэмнэлт (%), нөхөх хугацаа (сар) — бодитой муж ашигла (жишээ «8–12%», «18–30 сар»).
3. «### Дараагийн алхам» — нэг өгүүлбэр: үнэгүй 30 минутын зөвлөгөө эсвэл нарийвчилсан аудит.
Тоог өгөгдсөн тооцооноос л ав. Энэ бол урьдчилсан үнэлгээ гэдгийг нэг удаа дурд. Анхаарлын тэмдэг, эможи хэрэглэхгүй."""
    text = """=Харилцагч: {{ $json.input.client_name }}{{ $json.input.company ? ' (' + $json.input.company + ')' : '' }}
Барилгын төрөл: {{ $json.input.building_type }}
Тооцооны үр дүн (JSON): {{ JSON.stringify($json.metrics) }}"""
    mail = EMAIL_HTML_JS + r"""
const c = $('Тооцоо').first().json, rec = $('AI: зөвлөмж бичих').first().json.text || '';
const id = $('Тайлан хадгалах').first().json.id, m = c.metrics, to = (c.input.email || '').trim();
if (!to) return [];
const fmt = n => Number(n).toLocaleString('en-US').replace(/,/g, "'");
const md = s => esc(s).replace(/^### (.*)$/gm, '<h3 style="color:#1F5E3B;font-size:16px;margin:18px 0 6px">$1</h3>')
  .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/^\d+\. (.*)$/gm, '<p style="margin:0 0 8px;padding-left:14px;border-left:3px solid #8DC149">$1</p>')
  .replace(/^[-—] (.*)$/gm, '<p style="margin:0 0 6px">— $1</p>').replace(/\n{2,}/g, '<br>');
const kpi = (v, l, dark) => `<td style="padding:12px;background:${dark ? '#1F5E3B' : '#F4F7F4'};border-radius:8px;width:33%">
  <div style="font-size:20px;color:${dark ? '#fff' : '#1F5E3B'}">${v}</div><div style="font-size:11px;color:${dark ? '#8DC149' : '#3A8F5C'}">${l}</div></td>`;
const body = `<p style="margin:0 0 14px">Сайн байна уу, ${esc(c.input.client_name)}. Таны оруулсан мэдээллээр урьдчилсан эрчим хүчний балансыг тооцлоо.</p>
<table style="width:100%;border-spacing:6px;margin:0 -6px 10px"><tr>${kpi(m.grade + ' · ' + fmt(m.eui_kwh_m2), 'Зэрэглэл · кВт·ц/м²·жил', true)}${kpi(fmt(m.co2_t) + ' т', 'CO₂ ялгарал/жил')}${kpi(fmt(m.saving_cost_mid) + '₮', 'Боломжит хэмнэлт/жил (~20%)')}</tr></table>
${md(rec)}`;
return [{ json: { to, subject: `Эрчим хүчний урьдчилсан тайлан №${id} — ${c.input.company || c.input.client_name}`,
  html: brandEmail('Эрчим хүчний урьдчилсан тайлан', body),
  text: `Тайлан №${id}\nЗэрэглэл: ${m.grade} (${m.eui_kwh_m2} кВт·ц/м²·жил)\nCO2: ${m.co2_t} т/жил\n\n${rec}\n\nEnergy Balance · +976 8811 3855 · energybalance.mn` } }];
"""
    i = lambda k: f"$('Тооцоо').item.json.input.{k}"
    mm = lambda k: f"$('Тооцоо').item.json.metrics.{k}"
    nodes = [
        webhook(w, "eb-energy", mode="responseNode"),
        code(w, "Тооцоо", (220, 300), calc),
        chain(w, "AI: зөвлөмж бичих", (440, 300), sys, text),
        llm(w, (440, 520), 1600),
        pg(w, "Тайлан хадгалах", (740, 300),
           "INSERT INTO energy_reports (client_name, email, company, building_type, area_m2, elec_kwh_year, heat_gcal_year, "
           "elec_cost_year, heat_cost_year, metrics, recommendations) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11) RETURNING id",
           [i("client_name"), i("email") + " || ''", i("company") + " || ''", i("building_type"), i("area_m2"),
            i("elec_kwh_year"), i("heat_gcal_year") + " || 0", mm("elec_cost"), mm("heat_cost"),
            "JSON.stringify($('Тооцоо').item.json.metrics)", "$('AI: зөвлөмж бичих').item.json.text"]),
        node(w, "Хариу буцаах", "n8n-nodes-base.respondToWebhook", 1.4, [960, 300], {
            "respondWith": "json",
            "responseBody": "={{ JSON.stringify({ report_id: $json.id, metrics: $('Тооцоо').item.json.metrics, recommendations: $('AI: зөвлөмж бичих').item.json.text }) }}",
            "options": {},
        }),
        code(w, "И-мэйл бэлдэх", (1180, 300), mail),
        email(w, "Тайлан илгээх (SMTP)", (1400, 300), "={{ $json.to }}", "={{ $json.subject }}", "={{ $json.text }}", "={{ $json.html }}"),
    ]
    conn = main_conn("Webhook", "Тооцоо", "AI: зөвлөмж бичих", "Тайлан хадгалах", "Хариу буцаах", "И-мэйл бэлдэх", "Тайлан илгээх (SMTP)")
    sub(conn, M(), "AI: зөвлөмж бичих", "ai_languageModel")
    return workflow("ebAgent4Energy00", "Агент 4 · Эрчим хүчний шинжилгээ", nodes, conn)


def apply_layout(wf):
    """n8n editor дээрх байрлалыг docs/workflows зурагтай ижил болгоно."""
    from render_diagrams import layout
    pos = layout(wf)
    for n in wf["nodes"]:
        x, y, *_ = pos[n["name"]]
        n["position"] = [round(x), round(y)]
    return wf


if __name__ == "__main__":
    # workflows/gemini/*.json, workflows/claude/*.json — init.sh нь .env-ийн LLM_PROVIDER-ээр сонгоно
    for PROVIDER in ("gemini", "claude"):
        d = OUT / PROVIDER
        d.mkdir(parents=True, exist_ok=True)
        for fn, build in [("1_booking_agent.json", wf_booking), ("2_chat_agent.json", wf_chat),
                          ("3_content_agent.json", wf_content), ("4_energy_agent.json", wf_energy)]:
            (d / fn).write_text(json.dumps(apply_layout(build()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("✓", d / fn)
