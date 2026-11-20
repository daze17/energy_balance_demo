#!/usr/bin/env python3
"""n8n workflow JSON → n8n editor шиг харагдах зураг (SVG + PNG).

    python3 n8n/render_diagrams.py        →  docs/workflows/*.svg, *.png

PNG-г локал Google Chrome (headless)-оор үүсгэнэ. Ямар ч гадаад үйлчилгээ ашиглахгүй.
`layout()`-г build_workflows.py бас ашиглаж, n8n дээрх node-ийн байрлалыг ижил болгоно.
"""
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def _provider():
    import os
    v = os.environ.get("LLM_PROVIDER")
    env = ROOT.parent / ".env"
    if not v and env.exists():
        v = next((l.split("=", 1)[1].strip() for l in env.read_text().splitlines() if l.startswith("LLM_PROVIDER=")), None)
    return v or "gemini"


# DIAGRAM_MAILER=smtp|brevo|smtp2go — зурагт аль и-мэйл хувилбарыг харуулах (анхдагч: онлайн хувилбарын Brevo)
import os as _os
_m = _os.environ.get("DIAGRAM_MAILER", "brevo")
WF_DIR = ROOT / "workflows" / (_provider() if _m == "smtp" else f"{_provider()}-{_m}")


def _mail_api(n):
    """HTTP node нь и-мэйл API (Brevo/SMTP2GO) дуудаж байвал нэрийг нь буцаана."""
    u = n.get("parameters", {}).get("url", "")
    return "Brevo" if "brevo.com" in u else "SMTP2GO" if "smtp2go.com" in u else None
OUT = ROOT.parent / "docs" / "workflows"

TRIGGERS = {"n8n-nodes-base.webhook", "n8n-nodes-base.scheduleTrigger"}
WIDE = {"@n8n/n8n-nodes-langchain.agent": 300, "@n8n/n8n-nodes-langchain.chainLlm": 220}
NODE, SUB_D, COL_GAP, SUB_GAP, SUB_DY, ROW_GAP = 100, 80, 110, 130, 120, 90
SUB_ORDER = {"ai_languageModel": 0, "ai_memory": 1, "ai_outputParser": 2, "ai_tool": 3}
PORT_LABEL = {"ai_languageModel": "Chat Model*", "ai_memory": "Memory", "ai_tool": "Tool", "ai_outputParser": "Output Parser"}

STICKY = {
    "ebAgent1Booking0": ("Агент 1 · Захиалга баталгаажуулах", "Нүүр хуудасны форм → өгөгдлийн сан → AI хүн бүрт тохирсон баталгаажуулах и-мэйл бичнэ → харилцагчид илгээнэ → захиалгын төлөвийг «Илгээсэн» болгоно. Төрөл: Workflow + AI."),
    "ebAgent2Chat0000": ("Агент 2 · Харилцагчийн зөвлөх чат", "Вэб чат → AI Agent хэрэгслээ өөрөө сонгоно: үйлчилгээ, үнэ (DB), түгээмэл асуулт (DB), захиалга бүртгэх (API → Агент 1), менежерт шилжүүлэх (и-мэйл). Яриаг Postgres санах ойд хадгална. Төрөл: AI Agent."),
    "ebAgent3Content0": ("Агент 3 · Контент (Facebook)", "Админы товч эсвэл Да/Лх/Ба 09:00 → сэдэв сонгоно → AI Brand Book-ийн дуу хоолойгоор {caption, slides[]} JSON бэлдэнэ → «Хүлээгдэж буй» төлөвтэй хадгална → хүн батлахад Facebook-д гарна."),
    "ebAgent4Energy00": ("Агент 4 · Эрчим хүчний шинжилгээ", "Хэрэглээний өгөгдөл → Code: кВт·ц/м², CO₂, A–G зэрэглэл, зардал → AI хэмнэлтийн зөвлөмж → тайланг DB-д хадгална → вэбэд шууд хариу → харилцагчид и-мэйлээр илгээнэ."),
}


# ------------------------------------------------------------------ layout
def _sub_map(wf):
    """parent -> [(kind, subnode name)]"""
    subs = {}
    for src, outs in wf["connections"].items():
        for kind, lists in outs.items():
            if kind == "main":
                continue
            for lst in lists:
                for c in lst:
                    subs.setdefault(c["node"], []).append((kind, src))
    for p in subs:
        subs[p].sort(key=lambda t: SUB_ORDER.get(t[0], 9))  # tool-уудын дараалал build_workflows-ийнхоор
    return subs


def layout(wf):
    """Node бүрийн (x, y, w, h, kind) — n8n canvas координатаар."""
    nodes = {n["name"]: n for n in wf["nodes"]}
    subs = _sub_map(wf)
    sub_names = {s for lst in subs.values() for _, s in lst}
    edges = [(src, c["node"]) for src, outs in wf["connections"].items()
             for lst in outs.get("main", []) for c in lst]
    main = [n for n in nodes if n not in sub_names]
    level = {n: 0 for n in main}
    for _ in range(len(main)):
        for a, b in edges:
            level[b] = max(level[b], level[a] + 1)
    cols = {}
    for n in main:
        cols.setdefault(level[n], []).append(n)

    def size(name):
        t = nodes[name]["type"]
        if name in sub_names:
            return SUB_D, SUB_D, "sub"
        if t in WIDE:
            return WIDE[t], NODE, "wide"
        return NODE, NODE, "trigger" if t in TRIGGERS else "node"

    pos, x, sub_right = {}, 0, -1e9
    for lv in sorted(cols):
        names = cols[lv]
        col_w = max(size(n)[0] for n in names)
        spread = max(((len(subs.get(n, [])) - 1) * SUB_GAP + SUB_D for n in names if subs.get(n)), default=0)
        if spread:  # энэ баганын sub-node-ууд өмнөх баганынхтай давхцахгүй байх
            x = max(x, sub_right + 40 + spread / 2 - col_w / 2)
            sub_right = x + col_w / 2 + spread / 2
        total_h = len(names) * NODE + (len(names) - 1) * ROW_GAP
        y = -total_h / 2
        for n in names:
            w, h, k = size(n)
            pos[n] = (x + (col_w - w) / 2, y, w, h, k)
            y += NODE + ROW_GAP
        x += col_w + COL_GAP
    for parent, lst in subs.items():
        px, py, pw, ph, _ = pos[parent]
        cx0 = px + pw / 2 - (len(lst) - 1) * SUB_GAP / 2
        for i, (_, s) in enumerate(lst):
            pos[s] = (cx0 + i * SUB_GAP - SUB_D / 2, py + ph + SUB_DY, SUB_D, SUB_D, "sub")
    return pos


# ------------------------------------------------------------------ icons
def icon(t, cx, cy, s=40):
    h = s / 2
    g = f'<g transform="translate({cx - h},{cy - h}) scale({s / 40})">'
    if t.endswith(".webhook"):
        g += ('<g fill="none" stroke="#FF6D5A" stroke-width="3.2" stroke-linecap="round">'
              '<path d="M16 9a6 6 0 1 1 6 9l-6 10"/><path d="M8 26a6 6 0 1 0 10 6h12"/><path d="M32 27a6 6 0 1 0-4-11l-6-9"/></g>')
    elif t.endswith("scheduleTrigger"):
        g += ('<circle cx="20" cy="20" r="15" fill="none" stroke="#31C49F" stroke-width="3.2"/>'
              '<path d="M20 11v10l7 4" fill="none" stroke="#31C49F" stroke-width="3.2" stroke-linecap="round"/>')
    elif t.endswith(".code"):
        g += '<text x="20" y="27" text-anchor="middle" font-size="20" font-weight="700" fill="#FF9922" font-family="Menlo,monospace">{ }</text>'
    elif "postgres" in t.lower():
        g += ('<ellipse cx="20" cy="10" rx="13" ry="5" fill="#336791"/><path d="M7 10v20c0 3 6 5 13 5s13-2 13-5V10" fill="#336791"/>'
              '<path d="M7 17c0 3 6 5 13 5s13-2 13-5M7 24c0 3 6 5 13 5s13-2 13-5" fill="none" stroke="#fff" stroke-width="1.6"/>')
    elif t.endswith("emailSend") or t.endswith("emailSendTool"):
        g += ('<rect x="5" y="9" width="30" height="22" rx="3" fill="none" stroke="#4A6EE0" stroke-width="3"/>'
              '<path d="M6 11l14 11 14-11" fill="none" stroke="#4A6EE0" stroke-width="3" stroke-linejoin="round"/>')
    elif t.endswith("lmChatAnthropic"):
        g += ('<rect x="2" y="2" width="36" height="36" rx="9" fill="#D97757"/>'
              '<path d="M14.5 29l5-17h3l5 17h-3.3l-1.2-4.2h-5l-1.2 4.2zM18.8 22h3.4L20.5 16z" fill="#1F1F1F"/>')
    elif t.endswith("lmChatGoogleGemini"):
        g += ('<path d="M20 3C21 12 28 19 37 20C28 21 21 28 20 37C19 28 12 21 3 20C12 19 19 12 20 3Z" fill="#4285F4"/>'
              '<path d="M20 3C21 12 28 19 37 20C28 21 21 28 20 37Z" fill="#7B61FF" opacity=".55"/>')
    elif t.endswith(".agent"):
        g += ('<rect x="7" y="12" width="26" height="20" rx="5" fill="none" stroke="#1F1F1F" stroke-width="3"/>'
              '<path d="M20 6v6" stroke="#1F1F1F" stroke-width="3" stroke-linecap="round"/><circle cx="20" cy="5" r="2.5" fill="#1F1F1F"/>'
              '<circle cx="15" cy="21" r="2.6" fill="#1F1F1F"/><circle cx="25" cy="21" r="2.6" fill="#1F1F1F"/><path d="M15 27h10" stroke="#1F1F1F" stroke-width="2.4" stroke-linecap="round"/>')
    elif t.endswith("chainLlm"):
        g += ('<g fill="none" stroke="#1F1F1F" stroke-width="3" stroke-linecap="round">'
              '<path d="M17 23a6 6 0 0 0 9 1l5-5a6 6 0 0 0-9-8l-2 2"/><path d="M23 17a6 6 0 0 0-9-1l-5 5a6 6 0 0 0 9 8l2-2"/></g>')
    elif t.endswith("memoryPostgresChat"):
        g += ('<ellipse cx="20" cy="10" rx="13" ry="5" fill="#336791"/><path d="M7 10v20c0 3 6 5 13 5s13-2 13-5V10" fill="#336791"/>'
              '<path d="M14 21h12M14 26h8" stroke="#fff" stroke-width="2" stroke-linecap="round"/>')
    elif "httpRequest" in t:
        g += ('<g fill="none" stroke="#0088CC" stroke-width="2.8"><circle cx="20" cy="20" r="14"/>'
              '<path d="M6 20h28M20 6c5 4 5 24 0 28M20 6c-5 4-5 24 0 28"/></g>')
    elif t.endswith("respondToWebhook"):
        g += ('<g fill="none" stroke="#7A5AF8" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M16 11l-8 8 8 8"/><path d="M8 19h16a8 8 0 0 1 8 8v3"/></g>')
    else:
        g += '<circle cx="20" cy="20" r="12" fill="#999"/>'
    return g + "</g>"


def subtitle(n):
    t, p = n["type"], n["parameters"]
    if _mail_api(n):
        return f"send: email ({_mail_api(n)} API)"
    if t.endswith(".webhook"):
        return f'{p.get("httpMethod", "GET")}: /{p.get("path", "")}'
    if t.endswith("scheduleTrigger"):
        return "Cron: 0 9 * * 1,3,5"
    if t.endswith(".code"):
        return "JavaScript"
    if t.endswith(".postgres"):
        q = p.get("query", "").split()[0].upper() if p.get("query") else ""
        return f"Execute query: {q}"
    if t.endswith("emailSend"):
        return "send: email (SMTP)"
    if t.endswith("respondToWebhook"):
        return "Respond: JSON"
    if t.endswith(".agent"):
        return "Tools Agent"
    if t.endswith("chainLlm"):
        return "Basic LLM Chain"
    if t.endswith("lmChatAnthropic"):
        v = p.get("model", {}).get("value", "")
        return "claude-sonnet-5-5" if "__" in v else v
    if t.endswith("lmChatGoogleGemini"):
        v = p.get("modelName", "").replace("models/", "")
        return "gemini-3.5-flash-lite" if "__" in v else v
    if t.endswith("memoryPostgresChat"):
        return "Postgres Chat Memory"
    if t.endswith("postgresTool"):
        return "Postgres Tool"
    if t.endswith("emailSendTool"):
        return "Send Email Tool"
    if "httpRequest" in t:
        return f'HTTP {p.get("method", "GET")} Tool'
    return t.split(".")[-1]


# ------------------------------------------------------------------ svg
def esc(s):
    return html.escape(str(s), quote=True)


def label(x, y, w, name, sub, align="center", color="#1F1F1F"):
    return (f'<foreignObject x="{x}" y="{y}" width="{w}" height="64"><div xmlns="http://www.w3.org/1999/xhtml" '
            f'style="text-align:{align};font:600 13px/1.3 \'Open Sans\',Inter,-apple-system,Helvetica,sans-serif;color:{color}">'
            f'{esc(name)}<div style="font-weight:400;font-size:11.5px;color:#8A8A8A;margin-top:2px">{esc(sub)}</div></div></foreignObject>')


def render(wf):
    pos = layout(wf)
    nodes = {n["name"]: n for n in wf["nodes"]}
    subs = _sub_map(wf)
    xs = [p[0] for p in pos.values()] + [p[0] + p[2] for p in pos.values()]
    ys = [p[1] for p in pos.values()] + [p[1] + p[3] + 50 for p in pos.values()]
    PAD, TOP, STICKY_H = 70, 56, 120
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W = max(1100, maxx - minx + 2 * PAD)
    ox = (W - (maxx - minx)) / 2 - minx
    oy = TOP + 40 + STICKY_H + 60 - miny
    H = maxy + oy + PAD
    P = lambda name: (pos[name][0] + ox, pos[name][1] + oy, pos[name][2], pos[name][3], pos[name][4])

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">',
           '<defs><pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#D4D4D4"/></pattern>'
           '<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#9A9A9A"/></marker>'
           '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-opacity=".08"/></filter></defs>',
           f'<rect width="100%" height="100%" fill="#F7F7F7"/><rect y="{TOP}" width="100%" height="100%" fill="url(#dots)"/>']

    # n8n-ийн дээд мөр
    out.append(f'<rect width="100%" height="{TOP}" fill="#fff"/><line x1="0" y1="{TOP}" x2="{W}" y2="{TOP}" stroke="#E5E5E5"/>')
    out.append(f'<text x="24" y="34" font-family="Open Sans,Inter,Helvetica,sans-serif" font-size="14" fill="#8A8A8A">Overview /</text>'
               f'<text x="104" y="34" font-family="Open Sans,Inter,Helvetica,sans-serif" font-size="14" font-weight="600" fill="#1F1F1F">{esc(wf["name"])}</text>')
    tx = W / 2
    out.append(f'<rect x="{tx - 92}" y="12" width="184" height="32" rx="6" fill="#F2F2F2"/>'
               f'<rect x="{tx - 88}" y="15" width="88" height="26" rx="5" fill="#fff" filter="url(#sh)"/>'
               f'<text x="{tx - 44}" y="32" text-anchor="middle" font-family="Open Sans,Helvetica,sans-serif" font-size="12.5" font-weight="600" fill="#1F1F1F">Editor</text>'
               f'<text x="{tx + 46}" y="32" text-anchor="middle" font-family="Open Sans,Helvetica,sans-serif" font-size="12.5" fill="#8A8A8A">Executions</text>')
    out.append(f'<g transform="translate({W - 250},14)"><rect width="104" height="28" rx="6" fill="#EAF7EF" stroke="#BFE5CC"/>'
               '<circle cx="16" cy="14" r="4.5" fill="#29A35A"/><text x="28" y="18.5" font-family="Open Sans,Helvetica,sans-serif" font-size="12.5" font-weight="600" fill="#1E7A43">Published</text>'
               '<rect x="116" width="110" height="28" rx="6" fill="#FF6D5A"/><text x="171" y="18.5" text-anchor="middle" font-family="Open Sans,Helvetica,sans-serif" font-size="12.5" font-weight="600" fill="#fff">n8n · 47678</text></g>')

    # Sticky note (тайлбар)
    title, body = STICKY.get(wf["id"], (wf["name"], ""))
    sw = min(620, W - 2 * PAD)
    out.append(f'<rect x="{PAD}" y="{TOP + 40}" width="{sw}" height="{STICKY_H}" rx="6" fill="#FFF5D6" stroke="#F2DC9B"/>'
               f'<foreignObject x="{PAD + 16}" y="{TOP + 52}" width="{sw - 32}" height="{STICKY_H - 20}"><div xmlns="http://www.w3.org/1999/xhtml" '
               f'style="font:13px/1.45 \'Open Sans\',Inter,Helvetica,sans-serif;color:#5C4A12"><b style="font-size:15px;color:#3D3108">## {esc(title)}</b>'
               f'<div style="margin-top:6px">{esc(body)}</div></div></foreignObject>')

    # main холболтууд
    for src, outs in wf["connections"].items():
        for lst in outs.get("main", []):
            for c in lst:
                ax, ay, aw, ah, _ = P(src)
                bx, by, bw, bh, _ = P(c["node"])
                x1, y1, x2, y2 = ax + aw + 6, ay + ah / 2, bx - 6, by + bh / 2
                d = max(40, (x2 - x1) / 2)
                out.append(f'<path d="M{x1} {y1} C{x1 + d} {y1} {x2 - d} {y2} {x2 - 2} {y2}" fill="none" stroke="#9A9A9A" stroke-width="2" marker-end="url(#arr)"/>')

    # sub-node холболт (тасархай); портуудыг node-уудын дараа зурна
    ports = []
    for parent, lst in subs.items():
        px, py, pw, ph, _ = P(parent)
        kinds = []
        for k, _ in lst:
            if k not in kinds:
                kinds.append(k)
        port_x = {k: px + pw * (i + 1) / (len(kinds) + 1) for i, k in enumerate(kinds)}
        for k, s in lst:
            sx, sy, sw_, sh_, _ = P(s)
            x1, y1, x2, y2 = port_x[k], py + ph + 34, sx + sw_ / 2, sy
            out.append(f'<path d="M{x1} {y1} C{x1} {y1 + 45} {x2} {y2 - 45} {x2} {y2}" fill="none" stroke="#9A9A9A" stroke-width="2" stroke-dasharray="5 4"/>')
        for k, x in port_x.items():
            lab = PORT_LABEL.get(k, k)
            ports.append(f'<line x1="{x}" y1="{py + ph}" x2="{x}" y2="{py + ph + 14}" stroke="#9A9A9A" stroke-width="2" stroke-dasharray="3 3"/>'
                         f'<rect x="{x - 5}" y="{py + ph - 5}" width="10" height="10" transform="rotate(45 {x} {py + ph})" fill="#fff" stroke="#8A8A8A" stroke-width="1.6"/>'
                         f'<text x="{x}" y="{py + ph + 28}" text-anchor="middle" font-family="Open Sans,Helvetica,sans-serif" font-size="11" fill="#8A8A8A">{lab}</text>')

    # node-ууд
    for name, n in nodes.items():
        x, y, w, h, kind = P(name)
        t = n["type"]
        if kind == "sub":
            cx, cy, r = x + w / 2, y + h / 2, w / 2
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="#C7C7C7" stroke-width="2" filter="url(#sh)"/>')
            out.append(icon('emailSendTool' if _mail_api(n) else t, cx, cy, 36))
            out.append(f'<rect x="{cx - 5}" y="{y - 5}" width="10" height="10" transform="rotate(45 {cx} {y})" fill="#fff" stroke="#8A8A8A" stroke-width="1.6"/>')
            out.append(label(cx - 80, y + h + 8, 160, name, subtitle(n)))
            continue
        if kind == "trigger":
            out.append(f'<path d="M{x + 40} {y} H{x + w - 8} Q{x + w} {y} {x + w} {y + 8} V{y + h - 8} Q{x + w} {y + h} {x + w - 8} {y + h} H{x + 40} '
                       f'A40 {h / 2} 0 0 1 {x + 40} {y} Z" fill="#fff" stroke="#C7C7C7" stroke-width="2" filter="url(#sh)"/>')
            out.append(f'<text x="{x - 14}" y="{y + h / 2 + 6}" font-size="16" fill="#FF6D5A">⚡</text>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff" stroke="#C7C7C7" stroke-width="2" filter="url(#sh)"/>')
            out.append(f'<circle cx="{x - 1}" cy="{y + h / 2}" r="5" fill="#C7C7C7"/>')
        out.append(f'<circle cx="{x + w + 1}" cy="{y + h / 2}" r="5.5" fill="#fff" stroke="#9A9A9A" stroke-width="1.6"/>')
        if kind == "wide":
            out.append(icon('emailSend' if _mail_api(n) else t, x + 42, y + h / 2, 38))
            out.append(label(x + 72, y + h / 2 - 20, w - 82, name, subtitle(n), align="left"))
        else:
            out.append(icon('emailSend' if _mail_api(n) else t, x + w / 2, y + h / 2, 44))
            out.append(label(x + w / 2 - 80, y + h + 8, 160, name, subtitle(n)))
    out.extend(ports)
    out.append(f'<text x="{W - PAD}" y="{H - 24}" text-anchor="end" font-family="Open Sans,Helvetica,sans-serif" font-size="11" fill="#AAAAAA">'
               f'Energy Balance · n8n/workflows → render_diagrams.py</text>')
    out.append("</svg>")
    return "\n".join(out), int(W), int(H)


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def to_png(svg_path, png_path, w, h):
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or CHROME
    if not Path(chrome).exists():
        print("  (Chrome олдсонгүй — зөвхөн SVG)")
        return
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size={w},{h}", f"--screenshot={png_path}", svg_path.as_uri()],
                   check=True, capture_output=True, timeout=60)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for f in sorted(WF_DIR.glob("*.json")):
        wf = json.loads(f.read_text(encoding="utf-8"))
        svg, w, h = render(wf)
        sp, pp = OUT / f"{f.stem}.svg", OUT / f"{f.stem}.png"
        sp.write_text(svg, encoding="utf-8")
        to_png(sp, pp, w, h)
        print("✓", pp if pp.exists() else sp, f"{w}x{h}")
    sys.exit(0)
