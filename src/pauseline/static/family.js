(() => {
  const payer = window.PAUSELINE.payer;
  const SCAM_LABEL = {
    bank_safe_account: "Fake bank / 'safe account'",
    digital_arrest_or_government: "Fake police or government ('digital arrest')",
    family_emergency: "Fake family emergency",
    tech_support: "Fake tech support",
    romance: "Romance scam",
    prize_or_lottery: "Prize or lottery fee",
    investment_or_crypto: "Investment / crypto",
    fake_invoice_or_refund: "Fake refund or invoice",
    job_or_task: "Job / task scam",
    other: "Other warning signs",
  };
  const EVENT_LABEL = {
    "assessed": "Checked for warning signs",
    "answered": `${payer} answered the questions`,
    "paypal.order_created": "PayPal order created",
    "paypal.authorized": "PayPal is holding the money (authorised)",
    "paypal.captured": "PayPal captured the payment",
    "paypal.payout_sent": "PayPal payout sent to the recipient",
    "paypal.voided": "PayPal hold cancelled (voided), nothing charged",
    "paypal.error": "PayPal error",
    "paypal.authorization_denied": "PayPal denied the authorisation",
    "held.cooling_off": "Paused for the cooling-off period",
    "held.for_family": "Held for your decision",
    "family.notified": "You were notified",
    "family.approved": "You approved",
    "family.declined": "You declined",
    "cancelled": "Cancelled",
  };
  let lastPendingKey = "";

  function pendingCard(t) {
    const coolOff = t.decision === "cool_off";
    const flags = t.signals.filter((s) => s.name !== "ai_flag").map((s) => `<li>${escapeHtml(s.label)}${s.name.startsWith("answer:") ? "" : `: <em>${escapeHtml(s.evidence)}</em>`}</li>`).join("");
    const aiFlags = t.signals.filter((s) => s.name === "ai_flag").map((s) => `<li>${escapeHtml(s.evidence)}</li>`).join("");
    const answers = Object.entries(t.answers || {}).map(([q, a]) => `<li>${escapeHtml(q.replaceAll("_", " "))}: <strong>${escapeHtml(a)}</strong></li>`).join("");
    const release = coolOff && t.release_at ? `Sends automatically ${new Date(t.release_at * 1000).toLocaleString()} unless you decline.` : "Will not be sent unless you approve.";
    return `
      <article class="card stack" data-id="${escapeHtml(t.id)}">
        <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:baseline">
          <h3>${escapeHtml(money(t.amount, t.currency))} to ${escapeHtml(t.payee.name)} ${t.payee.known ? "" : '<span class="badge held">new payee</span>'}</h3>
          <span class="badge held">${coolOff ? "Paused" : "Held for you"} · risk ${Math.round((t.risk || 0) * 100)}%</span>
        </div>
        <div><strong>${escapeHtml(SCAM_LABEL[t.scam_type] || "Warning signs")}</strong>
          <p style="margin:4px 0 0">${escapeHtml(t.summary_for_family)}</p></div>
        <div><span class="small muted">${escapeHtml(payer)}'s words</span><blockquote>${escapeHtml(t.statement)}</blockquote></div>
        ${flags || aiFlags ? `<div><span class="small muted">Why it was paused</span><ul class="chips">${flags}${aiFlags}</ul></div>` : ""}
        ${answers ? `<div><span class="small muted">${escapeHtml(payer)}'s answers</span><ul class="chips">${answers}</ul></div>` : ""}
        <p class="small muted">${escapeHtml(release)} The money is held by PayPal (authorisation ${escapeHtml(t.authorization_id || "")}); ${escapeHtml(payer)} has not been charged.</p>
        <div><label for="note-${escapeHtml(t.id)}">Note to ${escapeHtml(payer)} (optional)</label>
          <input id="note-${escapeHtml(t.id)}" type="text" placeholder="I'll call you in a minute, Ma"></div>
        <div class="btn-row">
          <button class="btn btn-stop" data-act="decline" type="button">Decline and cancel</button>
          <button class="btn btn-ok" data-act="approve" type="button">It's genuine, release it</button>
        </div>
      </article>`;
  }

  async function decide(id, approve) {
    const note = $(`#note-${CSS.escape(id)}`)?.value || "";
    await api(`/api/transfers/${id}/family`, { method: "POST", body: { approve, note } });
    lastPendingKey = "";
    await refresh();
  }

  async function refresh() {
    let data;
    try { data = await api("/api/family/overview"); } catch (_) { return; }
    const key = data.pending.map((t) => t.id + t.updated_at).join("|");
    if (key !== lastPendingKey) {   // don't wipe a note someone is typing
      lastPendingKey = key;
      const box = $("#pending");
      box.innerHTML = data.pending.length ? data.pending.map(pendingCard).join("") : '<p class="empty">Nothing is waiting. You\'ll see it here the moment a payment is paused.</p>';
      $$("article[data-id]", box).forEach((card) => {
        $$("button[data-act]", card).forEach((b) => b.addEventListener("click", async () => {
          b.disabled = true;
          try { await decide(card.dataset.id, b.dataset.act === "approve"); } catch (e) { b.disabled = false; window.alert(e.message); }
        }));
      });
    }
    $("#recent").innerHTML = data.recent.length ? data.recent.map((t) => `
      <tr><td>${timeAgo(t.created_at)}</td><td>${escapeHtml(t.payee.name)}</td><td>${escapeHtml(money(t.amount, t.currency))}</td>
      <td><span class="badge ${escapeHtml(t.status)}">${escapeHtml(STATUS_LABEL[t.status] || t.status)}</span></td></tr>`).join("")
      : '<tr><td colspan="4" class="empty">No payments yet.</td></tr>';
    $("#events").innerHTML = data.events.map((e) => {
      let detail = "";
      try { const d = JSON.parse(e.detail); detail = Object.entries(d).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · "); } catch (_) { detail = e.detail; }
      return `<li><span class="muted">${timeAgo(e.at)}</span><span>${escapeHtml(EVENT_LABEL[e.kind] || e.kind)}<br><code>${escapeHtml(detail)}</code></span></li>`;
    }).join("");
  }

  refresh();
  setInterval(refresh, 3000);
})();
