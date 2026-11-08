(() => {
  const payer = window.PAUSELINE.payer;
  const SCAM_LABEL = {
    bank_safe_account: "Fake bank or 'safe account'",
    digital_arrest_or_government: "Fake police or government ('digital arrest')",
    family_emergency: "Fake family emergency",
    tech_support: "Fake tech support",
    romance: "Romance scam",
    prize_or_lottery: "Prize or lottery fee",
    investment_or_crypto: "Investment or crypto",
    fake_invoice_or_refund: "Fake refund or invoice",
    job_or_task: "Job or task scam",
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
    "family.notified": "Added to this page",
    "family.approved": "You approved",
    "family.declined": "You declined",
    "cancelled": "Cancelled",
  };
  let lastPendingKey = null;  // null, not "": an empty pending list has the key ""
  let seenPending = null;  // null until the first load, so old holds don't raise an alert

  function pendingCard(t) {
    const coolOff = t.decision === "cool_off";
    const flags = t.signals.filter((s) => s.name !== "ai_flag").map((s) => `<li>${escapeHtml(s.label)}${s.name.startsWith("answer:") ? "" : `: <em>${escapeHtml(s.evidence)}</em>`}</li>`).join("");
    const aiFlags = t.signals.filter((s) => s.name === "ai_flag").map((s) => `<li>${escapeHtml(s.evidence)}</li>`).join("");
    const answers = Object.entries(t.answers || {}).map(([q, a]) => `<li>${escapeHtml(q.replaceAll("_", " "))}: <strong>${escapeHtml(a)}</strong></li>`).join("");
    const release = coolOff && t.release_at ? `Sends automatically on ${new Date(t.release_at * 1000).toLocaleString()} unless you decline.` : "Will not be sent unless you approve.";
    return `
      <article class="slip stack" data-id="${escapeHtml(t.id)}">
        <div class="slip-head">
          <h3>${escapeHtml(money(t.amount, t.currency))} to ${escapeHtml(t.payee.name)}${t.payee.known ? "" : " (new payee)"}</h3>
          <span class="tag held">${coolOff ? "Paused" : "Held for you"}, risk ${Math.round((t.risk || 0) * 100)}%</span>
        </div>
        <div><strong>${escapeHtml(SCAM_LABEL[t.scam_type] || "Warning signs")}</strong>
          <p>${escapeHtml(t.summary_for_family)}</p></div>
        <div><span class="small muted">${escapeHtml(payer)}'s words</span><blockquote>${escapeHtml(t.statement)}</blockquote></div>
        ${flags || aiFlags ? `<div><span class="small muted">Why it was paused</span><ul class="reasons">${flags}${aiFlags}</ul></div>` : ""}
        ${answers ? `<div><span class="small muted">${escapeHtml(payer)}'s answers</span><ul class="reasons">${answers}</ul></div>` : ""}
        <p class="small muted">${escapeHtml(release)} PayPal is holding the money (authorisation ${escapeHtml(t.authorization_id || "")}), and ${escapeHtml(payer)} has not been charged.</p>
        <div><label for="note-${escapeHtml(t.id)}">Note to ${escapeHtml(payer)} (optional)</label>
          <input id="note-${escapeHtml(t.id)}" type="text" placeholder="I'll call you in a minute, Ma"></div>
        <div class="btn-row">
          <button class="btn btn-stop" data-act="decline" type="button">Decline and cancel</button>
          <button class="btn btn-secondary" data-act="approve" type="button">It's genuine, release it</button>
        </div>
      </article>`;
  }

  async function decide(id, approve) {
    const note = $(`#note-${CSS.escape(id)}`)?.value || "";
    await api(`/api/transfers/${id}/family`, { method: "POST", body: { approve, note } });
    lastPendingKey = null;
    await refresh();
  }

  function alertNewHolds(pending) {
    const ids = new Set(pending.map((t) => t.id));
    if (seenPending) {
      const fresh = pending.filter((t) => !seenPending.has(t.id));
      if (fresh.length && "Notification" in window && Notification.permission === "granted") {
        const t = fresh[0];
        new Notification(`${payer}'s payment needs you`, { body: `${money(t.amount, t.currency)} to ${t.payee.name}` });
      }
    }
    seenPending = ids;
    document.title = pending.length ? `(${pending.length}) Family view` : "Family view";
  }

  function setUpAlerts() {
    const btn = $("#alerts");
    if (!("Notification" in window)) return;
    const paint = () => {
      btn.classList.toggle("hidden", Notification.permission === "granted");
      if (Notification.permission === "denied") { btn.disabled = true; btn.textContent = "Alerts are blocked in this browser"; }
    };
    btn.addEventListener("click", async () => { await Notification.requestPermission(); paint(); });
    paint();
  }

  async function refresh() {
    let data;
    try { data = await api("/api/family/overview"); }
    catch (e) { if (e.status === 401) { setFamilyPin(""); location.reload(); } return; }
    alertNewHolds(data.pending);
    const key = data.pending.map((t) => t.id + t.updated_at).join("|");
    if (key !== lastPendingKey) {   // don't wipe a note someone is typing
      lastPendingKey = key;
      const box = $("#pending");
      box.innerHTML = data.pending.length ? data.pending.map(pendingCard).join("") : `<p class="empty">Nothing is waiting. Keep this page open to see a paused payment within seconds.</p>`;
      $$("article[data-id]", box).forEach((card) => {
        $$("button[data-act]", card).forEach((b) => b.addEventListener("click", async () => {
          b.disabled = true;
          try { await decide(card.dataset.id, b.dataset.act === "approve"); } catch (e) { b.disabled = false; window.alert(e.message); }
        }));
      });
    }
    $("#recent").innerHTML = data.recent.length ? data.recent.map((t) => `
      <tr><td>${timeAgo(t.created_at)}</td><td>${escapeHtml(t.payee.name)}</td><td>${escapeHtml(money(t.amount, t.currency))}</td>
      <td><span class="tag ${escapeHtml(t.delivery_failed ? "failed" : t.status)}">${escapeHtml(t.delivery_failed ? "Not delivered" : (STATUS_LABEL[t.status] || t.status))}</span></td></tr>`).join("")
      : '<tr><td colspan="4" class="empty">No payments yet.</td></tr>';
    $("#events").innerHTML = data.events.map((e) => {
      let detail = "";
      try { const d = JSON.parse(e.detail); detail = Object.entries(d).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(", "); } catch (_) { detail = e.detail; }
      return `<li><span class="muted">${timeAgo(e.at)}</span><span>${escapeHtml(EVENT_LABEL[e.kind] || e.kind.replace("webhook.", "PayPal event: "))}<br><code>${escapeHtml(detail)}</code></span></li>`;
    }).join("");
  }

  requireFamily(() => {
    setUpAlerts();
    refresh();
    setInterval(refresh, 3000);
  });
})();
