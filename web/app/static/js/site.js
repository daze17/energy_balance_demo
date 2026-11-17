// Нүүр хуудасны эрчим хүчний тооцоолуур (агент №4). Чат виджет: chat-widget.js
(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ---------- Эрчим хүчний тооцоо ----------
  const ef = $("#energy-form"), out = $("#energy-result"), btn = $("#energy-btn");
  const GRADES = ["A", "B", "C", "D", "E", "F", "G"];
  const fmt = (n, d = 0) => Number(n).toLocaleString("en-US", { maximumFractionDigits: d }).replace(/,/g, "'");
  // Brand Book 10: A–G зэрэглэл зөвхөн ногоон, бараан нь хамгийн сайн
  const ladder = (g) => '<div class="ladder">' + GRADES.map((x, i) =>
    `<div class="g-${x}${x === g ? " on" : ""}" style="width:${38 + i * 9}%"><span>${x}</span>${x === g ? "<span>◀ таны барилга</span>" : ""}</div>`).join("") + "</div>";

  ef.onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(ef).entries());
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> AI шинжилж байна…';
    out.innerHTML = '<p class="muted"><span class="spinner"></span> Тооцоолж, зөвлөмж бичиж байна (10–20 сек)…</p>';
    try {
      const r = await fetch("/api/energy", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
      const j = await r.json();
      if (!r.ok || j.error) throw new Error(j.error || j.detail || "Алдаа");
      const m = j.metrics || {};
      out.innerHTML = `
        <div class="eyebrow">Эрчим хүчний зэрэглэл (урьдчилсан) · кВт·ц/м²·жил</div>
        <p style="margin:4px 0 0"><b style="color:var(--green)">${esc(m.grade || "?")} зэрэглэл</b> — <span class="muted">${esc(m.grade_text || "")}</span></p>
        ${ladder(m.grade)}
        <div class="metric-grid">
          <div class="d"><b>${fmt(m.eui_kwh_m2)}</b><small>кВт·ц/м²·жил</small></div>
          <div><b>${fmt(m.total_kwh)}</b><small>Нийт кВт·ц/жил</small></div>
          <div><b>${fmt(m.co2_t, 1)} т</b><small>CO₂ ялгарал/жил</small></div>
          <div><b>${fmt(m.total_cost)}₮</b><small>Эрчим хүчний зардал/жил</small></div>
          <div><b>${fmt(m.saving_cost_mid)}₮</b><small>Боломжит хэмнэлт (~20%)</small></div>
          <div><b>${fmt(m.saving_co2_mid, 1)} т</b><small>CO₂ бууралт/жил</small></div>
        </div>
        <div class="card" style="background:#fff">${j.recommendations_html || ""}</div>
        <p class="muted" style="font-size:.8rem;margin-bottom:0">Тайлан #${esc(j.report_id || "")}${data.email ? " · и-мэйлээр илгээгдлээ" : ""}. Урьдчилсан тооцоо — нарийн дүнг аудитаар тодорхойлно.</p>`;
    } catch (err) {
      out.innerHTML = `<p style="color:var(--danger)">${esc(err.message)}</p>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = "Шинжилгээ хийх";
    }
  };
})();
