/*!
 * Energy Balance — AI зөвлөх чат виджет (Агент №2)
 * Аль ч вэб сайтад нэг мөрөөр суулгана:
 *   <script src="http://localhost:47080/static/js/chat-widget.js" defer></script>
 * Тохиргоо (заавал биш): data-api="https://..."  data-open="true"  data-teaser="false"
 * Shadow DOM ашигладаг тул тухайн сайтын CSS-тэй зөрчилдөхгүй.
 */
(function () {
  if (window.__ebChatLoaded) return;
  window.__ebChatLoaded = true;

  const script = document.currentScript || document.querySelector('script[src*="chat-widget.js"]');
  const API = ((script && script.dataset.api) || (script ? new URL(script.src).origin : "")).replace(/\/$/, "");
  const AUTO_OPEN = script && script.dataset.open === "true";
  const TEASER = !(script && script.dataset.teaser === "false");
  const LOGO = API + "/brand/logo.svg";

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    sget(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
    sset(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} },
  };

  const CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
  .launch { position: fixed; right: 22px; bottom: 22px; z-index: 2147483000; width: 62px; height: 62px; border-radius: 50%;
    border: 0; padding: 0; cursor: pointer; background: #1F5E3B; box-shadow: 0 12px 30px rgba(31,94,59,.35);
    display: grid; place-items: center; transition: transform .2s; }
  .launch:hover { transform: scale(1.06); }
  .launch img { width: 62px; height: 62px; border-radius: 50%; }
  .launch .x { display: none; color: #fff; font-size: 26px; line-height: 1; }
  .launch.open img { display: none; } .launch.open .x { display: block; }
  .dot { position: absolute; top: 2px; right: 2px; width: 14px; height: 14px; border-radius: 50%; background: #8DC149; border: 2px solid #fff; }
  .teaser { position: fixed; right: 22px; bottom: 96px; z-index: 2147483000; max-width: 270px; background: #fff; color: #183A27;
    border: 1px solid #E1E8E2; border-radius: 14px 14px 4px 14px; padding: 12px 34px 12px 14px; font-size: 14px; line-height: 1.45;
    box-shadow: 0 12px 30px rgba(0,0,0,.12); cursor: pointer; animation: up .3s ease; }
  .teaser b { color: #1F5E3B; font-weight: 600; }
  .teaser .close { position: absolute; top: 6px; right: 8px; border: 0; background: none; color: #5E7466; cursor: pointer; font-size: 16px; }
  .box { position: fixed; right: 22px; bottom: 96px; z-index: 2147483000; width: 380px; height: 600px; max-height: calc(100vh - 120px);
    background: #fff; border-radius: 18px; box-shadow: 0 24px 60px rgba(0,0,0,.2); display: none; flex-direction: column;
    overflow: hidden; border: 1px solid #E1E8E2; animation: up .25s ease; }
  .box.open { display: flex; }
  @keyframes up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
  .hd { background: #1F5E3B; color: #fff; padding: 14px 16px; display: flex; gap: 12px; align-items: center; position: relative; overflow: hidden; }
  .hd::after { content: ""; position: absolute; right: -40px; top: -50px; width: 130px; height: 130px; border-radius: 50%; background: #3A8F5C; opacity: .55; }
  .hd img { width: 40px; height: 40px; border-radius: 50%; box-shadow: 0 0 0 2px #fff; position: relative; z-index: 1; }
  .hd .t { position: relative; z-index: 1; flex: 1; }
  .hd b { font-weight: 600; font-size: 15px; display: block; }
  .hd small { font-size: 12px; color: #D3E5D8; display: flex; align-items: center; gap: 6px; }
  .hd small::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: #8DC149; }
  .hd .icon { position: relative; z-index: 1; border: 0; background: rgba(255,255,255,.12); color: #fff; width: 32px; height: 32px;
    border-radius: 8px; cursor: pointer; font-size: 15px; }
  .hd .icon:hover { background: rgba(255,255,255,.22); }
  .log { flex: 1; overflow-y: auto; padding: 16px 14px; background: #F4F7F4; display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth; }
  .row { display: flex; gap: 8px; align-items: flex-end; }
  .row.me { justify-content: flex-end; }
  .row img { width: 26px; height: 26px; border-radius: 50%; flex: none; }
  .msg { max-width: 80%; padding: 10px 13px; border-radius: 16px; font-size: 14px; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; }
  .bot .msg { background: #fff; color: #183A27; border: 1px solid #E1E8E2; border-bottom-left-radius: 4px; }
  .me .msg { background: #1F5E3B; color: #fff; border-bottom-right-radius: 4px; }
  .msg a { color: #3A8F5C; } .me .msg a { color: #8DC149; }
  .time { font-size: 10.5px; color: #8A9A90; margin: -4px 34px 0; }
  .me + .time { text-align: right; margin-right: 2px; }
  .typing { display: inline-flex; gap: 4px; padding: 12px 14px; }
  .typing span { width: 7px; height: 7px; border-radius: 50%; background: #3A8F5C; animation: b 1.2s infinite; }
  .typing span:nth-child(2) { animation-delay: .15s; } .typing span:nth-child(3) { animation-delay: .3s; }
  @keyframes b { 0%, 60%, 100% { opacity: .3; transform: none; } 30% { opacity: 1; transform: translateY(-4px); } }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; padding: 8px 14px 10px; background: #F4F7F4; border-top: 1px solid #E9EFEA; }
  .chips button { border: 1px solid #3A8F5C; background: #fff; color: #1F5E3B; border-radius: 999px; padding: 6px 11px;
    font-size: 12.5px; cursor: pointer; }
  .chips button:hover { background: #1F5E3B; color: #fff; }
  form { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #E1E8E2; background: #fff; align-items: flex-end; }
  textarea { flex: 1; resize: none; border: 1px solid #E1E8E2; border-radius: 12px; padding: 10px 12px; font-size: 14px; max-height: 110px;
    outline: none; color: #183A27; line-height: 1.4; }
  textarea:focus { border-color: #3A8F5C; box-shadow: 0 0 0 3px rgba(58,143,92,.15); }
  .send { width: 42px; height: 42px; border-radius: 12px; border: 0; background: #1F5E3B; cursor: pointer; display: grid; place-items: center; flex: none; }
  .send:disabled { opacity: .45; cursor: default; }
  .send svg { width: 18px; height: 18px; fill: none; stroke: #fff; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
  .foot { text-align: center; font-size: 10.5px; color: #8A9A90; padding: 0 0 8px; background: #fff; letter-spacing: .04em; }
  @media (max-width: 520px) {
    .box { right: 0; bottom: 0; width: 100vw; height: 100dvh; max-height: none; border-radius: 0; }
    .launch.open { display: none; }
  }`;

  const host = document.createElement("div");
  host.id = "eb-chat-widget";
  document.body.appendChild(host);
  const root = host.attachShadow({ mode: "open" });
  root.innerHTML = `<style>${CSS}</style>
    <button class="launch" aria-label="Energy Balance зөвлөхтэй чатлах"><img src="${LOGO}" alt=""><span class="x">×</span><span class="dot"></span></button>
    <div class="box" role="dialog" aria-label="Energy Balance AI зөвлөх">
      <div class="hd"><img src="${LOGO}" alt=""><div class="t"><b>Energy Balance зөвлөх</b><small>AI агент · 24/7 онлайн</small></div>
        <button class="icon human" title="Менежертэй холбогдох">☎</button><button class="icon reset" title="Шинэ яриа">↻</button><button class="icon min" title="Хаах">–</button></div>
      <div class="log" aria-live="polite"></div>
      <div class="chips"></div>
      <form><textarea rows="1" placeholder="Асуултаа бичнэ үү…" aria-label="Мессеж"></textarea>
        <button class="send" type="submit" aria-label="Илгээх" disabled><svg viewBox="0 0 24 24"><path d="M4 12l16-8-6 16-2-7z"/></svg></button></form>
      <div class="foot">ENERGY BALANCE · AI хариулт алдаатай байж болно</div>
    </div>`;

  const $ = (s) => root.querySelector(s);
  const launch = $(".launch"), box = $(".box"), log = $(".log"), chips = $(".chips"), form = $("form"), input = $("textarea"), send = $(".send");
  const WELCOME = "Сайн байна уу. Би Energy Balance-ийн AI зөвлөх.\nЭрчим хүчний аудит, барилгын гэрчилгээ, ISO 50001, үнэ, хугацааны талаар асуугаарай. Хүсвэл үнэгүй зөвлөгөөний цагийг тань шууд бүртгэнэ.";
  const QUICK = ["Барилгын аудит хэд вэ?", "Ногоон зээлд юу хэрэгтэй вэ?", "Аудит хэрхэн явагддаг вэ?", "Үнэгүй зөвлөгөө авмаар байна"];

  let sid = store.get("eb_chat_sid");
  let busy = false, loaded = false;

  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmt = (t) => esc(t)
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>')
    .replace(/(\+?976[\s-]?\d{4}[\s-]?\d{4}|\b\d{4}[\s-]\d{4}\b)/g, (m) => `<a href="tel:${m.replace(/[\s-]/g, "")}">${m}</a>`);
  const hhmm = (d) => (d ? new Date(d) : new Date()).toLocaleTimeString("mn-MN", { hour: "2-digit", minute: "2-digit" });

  function bubble(text, who, when) {
    const row = document.createElement("div");
    row.className = "row " + (who === "user" ? "me" : "bot");
    row.innerHTML = (who === "user" ? "" : `<img src="${LOGO}" alt="">`) + `<div class="msg">${fmt(text)}</div>`;
    log.appendChild(row);
    const t = document.createElement("div");
    t.className = "time";
    t.textContent = hhmm(when);
    log.appendChild(t);
    log.scrollTop = log.scrollHeight;
  }
  function typing(on) {
    const ex = root.querySelector(".typing-row");
    if (ex) ex.remove();
    if (!on) return;
    const row = document.createElement("div");
    row.className = "row bot typing-row";
    row.innerHTML = `<img src="${LOGO}" alt=""><div class="msg typing"><span></span><span></span><span></span></div>`;
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }
  function renderChips(list) {
    chips.innerHTML = "";
    chips.style.display = list.length ? "flex" : "none";
    list.forEach((q) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = q;
      b.onclick = () => ask(q);
      chips.appendChild(b);
    });
  }

  async function loadHistory() {
    if (loaded) return;
    loaded = true;
    log.innerHTML = "";
    bubble(WELCOME, "assistant");
    if (!sid) return renderChips(QUICK);
    try {
      const r = await fetch(`${API}/api/chat/history?session_id=${encodeURIComponent(sid)}`);
      const j = await r.json();
      (j.messages || []).forEach((m) => bubble(m.content, m.role, m.created_at));
      renderChips(j.messages && j.messages.length ? [] : QUICK);
    } catch (e) { renderChips(QUICK); }
  }

  async function ask(text) {
    text = (text || "").trim();
    if (!text || busy) return;
    busy = true;
    renderChips([]);
    bubble(text, "user");
    input.value = "";
    autosize();
    typing(true);
    try {
      const r = await fetch(`${API}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid, message: text, page: location.href.slice(0, 300) }) });
      const j = await r.json();
      sid = j.session_id || sid;
      store.set("eb_chat_sid", sid);
      typing(false);
      bubble(j.reply || "Уучлаарай, хариу ирсэнгүй. Та +976 8811 3855 дугаарт залгана уу.", "assistant");
    } catch (e) {
      typing(false);
      bubble("Холболтын алдаа гарлаа. Дахин оролдох эсвэл +976 8811 3855 дугаарт залгана уу.", "assistant");
    }
    busy = false;
    send.disabled = !input.value.trim();
    input.focus();
  }

  function openBox(v) {
    const open = v === undefined ? !box.classList.contains("open") : v;
    box.classList.toggle("open", open);
    launch.classList.toggle("open", open);
    const t = root.querySelector(".teaser");
    if (t) t.remove();
    $(".dot").style.display = "none";
    store.sset("eb_teased", "1");
    if (open) { loadHistory(); setTimeout(() => input.focus(), 50); }
  }
  function autosize() { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 110) + "px"; }

  launch.onclick = () => openBox();
  $(".min").onclick = () => openBox(false);
  $(".human").onclick = () => ask("Менежертэй шууд холбогдмоор байна.");
  $(".reset").onclick = () => { sid = null; store.set("eb_chat_sid", ""); loaded = false; loadHistory(); };
  input.addEventListener("input", () => { autosize(); send.disabled = !input.value.trim() || busy; });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(input.value); } });
  form.onsubmit = (e) => { e.preventDefault(); ask(input.value); };
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && box.classList.contains("open")) openBox(false); });
  // Сайтын бусад товч чатыг нээх боломж: <a href="#" data-eb-chat="Асуулт">…</a>
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("[data-eb-chat]");
    if (!a) return;
    e.preventDefault();
    openBox(true);
    if (a.dataset.ebChat) setTimeout(() => ask(a.dataset.ebChat), 300);
  });
  window.EBChat = { open: () => openBox(true), close: () => openBox(false), ask: (q) => { openBox(true); setTimeout(() => ask(q), 300); } };

  if (AUTO_OPEN) openBox(true);
  else if (TEASER && !store.sget("eb_teased")) {
    setTimeout(() => {
      if (box.classList.contains("open") || store.sget("eb_teased")) return;
      const t = document.createElement("div");
      t.className = "teaser";
      t.innerHTML = `<button class="close" aria-label="Хаах">×</button><b>Эрчим хүчний зардлаа бууруулах уу?</b><br>Асуух зүйлээ бичээрэй — AI зөвлөх 24/7 хариулна.`;
      t.onclick = (e) => { if (e.target.classList.contains("close")) { t.remove(); store.sset("eb_teased", "1"); } else openBox(true); };
      root.appendChild(t);
    }, 5000);
  }
})();
