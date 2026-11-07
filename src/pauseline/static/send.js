(() => {
  const cfg = window.PAUSELINE;
  let payeeId = null;
  let transfer = null;
  let answers = {};
  let pollTimer = null;

  const show = (id) => {
    for (const s of ["step-details", "step-questions", "step-pay", "step-result"]) $("#" + s).classList.toggle("hidden", s !== id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const fail = (el, msg) => { el.textContent = msg; el.classList.remove("hidden"); };

  // --- payee selection
  $$(".payee").forEach((btn) => btn.addEventListener("click", () => {
    $$(".payee").forEach((b) => b.setAttribute("aria-pressed", "false"));
    btn.setAttribute("aria-pressed", "true");
    const isNew = btn.id === "new-payee-toggle";
    $("#new-payee").classList.toggle("hidden", !isNew);
    payeeId = isNew ? "__new__" : btn.dataset.payee;
  }));

  // --- speech input (Web Speech API; Chrome / Edge)
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = $("#mic");
  if (!SR) { mic.disabled = true; mic.title = "Speech input needs Chrome or Edge"; }
  let rec = null;
  mic.addEventListener("click", () => {
    if (!SR) return;
    if (rec) { rec.stop(); return; }
    rec = new SR();
    rec.lang = $("#mic-lang").value;
    rec.interimResults = true;
    const base = $("#statement").value ? $("#statement").value + " " : "";
    rec.onresult = (e) => {
      $("#statement").value = base + Array.from(e.results).map((r) => r[0].transcript).join(" ");
    };
    rec.onend = async () => {
      mic.setAttribute("aria-pressed", "false"); rec = null;
      // Fill amount / payee from speech if the person said them ("send 200 to Rahul ...")
      try {
        const intent = await api("/api/intent", { method: "POST", body: { text: $("#statement").value } });
        if (intent.amount && !$("#amount").value) $("#amount").value = intent.amount;
        if (intent.payee && !payeeId) $(`.payee[data-payee="${intent.payee.id}"]`)?.click();
      } catch (_) { /* optional */ }
    };
    mic.setAttribute("aria-pressed", "true");
    rec.start();
  });

  // --- step 1 -> assess
  $("#continue").addEventListener("click", async () => {
    const err = $("#details-error"); err.classList.add("hidden");
    const amount = parseFloat($("#amount").value);
    const statement = $("#statement").value.trim();
    if (!payeeId) return fail(err, "Please choose who you are paying.");
    if (!(amount > 0)) return fail(err, "Please enter an amount.");
    if (!statement) return fail(err, "Please tell us, in a few words, what the payment is for.");
    $("#continue").disabled = true;
    try {
      let pid = payeeId;
      if (pid === "__new__") {
        const name = $("#np-name").value.trim();
        if (!name) { $("#continue").disabled = false; return fail(err, "Please enter their name."); }
        const p = await api("/api/payees", { method: "POST", body: { name, email: $("#np-email").value.trim(), known: false } });
        pid = p.id;
      }
      transfer = await api("/api/transfers", { method: "POST", body: { payee_id: pid, amount, statement } });
      transfer.questions.length ? renderQuestions() : toPay();
    } catch (e) {
      fail(err, e.message);
    } finally {
      $("#continue").disabled = false;
    }
  });

  // --- step 2: questions
  function renderQuestions() {
    answers = {};
    const box = $("#questions");
    box.innerHTML = transfer.questions.map((q) => `
      <div class="question" data-q="${escapeHtml(q.id)}">
        <p>${escapeHtml(q.text)}</p>
        <div class="btn-row">
          <button type="button" class="btn btn-secondary choice" data-a="yes" aria-pressed="false">Yes</button>
          <button type="button" class="btn btn-secondary choice" data-a="no" aria-pressed="false">No</button>
        </div>
      </div>`).join("");
    $$(".question", box).forEach((qel) => {
      $$(".choice", qel).forEach((b) => b.addEventListener("click", () => {
        $$(".choice", qel).forEach((x) => x.setAttribute("aria-pressed", "false"));
        b.setAttribute("aria-pressed", "true");
        answers[qel.dataset.q] = b.dataset.a;
        $("#answers-continue").disabled = Object.keys(answers).length < transfer.questions.length;
      }));
    });
    show("step-questions");
    speak(transfer.questions[0].text);
  }

  $("#answers-continue").addEventListener("click", async () => {
    $("#answers-continue").disabled = true;
    try {
      transfer = await api(`/api/transfers/${transfer.id}/answers`, { method: "POST", body: { answers } });
      toPay();
    } catch (e) {
      alertResult("stop", "Something went wrong", e.message);
    }
  });

  // --- step 3: pay
  function toPay() {
    const t = transfer;
    $("#pay-title").textContent = `Pay ${money(t.amount, t.currency)} to ${t.payee.name}`;
    const notice = $("#pay-notice");
    if (t.decision && t.decision !== "allow") {
      notice.innerHTML = `<h2>We will hold this payment for a check</h2><p>${escapeHtml(t.message_to_payer)}</p>`;
      notice.classList.remove("hidden");
    } else {
      notice.classList.add("hidden");
    }
    show("step-pay");
    if (cfg.live) renderPayPalButtons(); else $("#demo-pay").onclick = demoPay;
  }

  async function createOrder() {
    const r = await api(`/api/transfers/${transfer.id}/order`, { method: "POST" });
    return r.order_id;
  }

  async function onApproved() {
    transfer = await api(`/api/transfers/${transfer.id}/approved`, { method: "POST" });
    renderResult();
  }

  function renderPayPalButtons() {
    const el = $("#paypal-buttons");
    if (el.dataset.rendered) return;
    el.dataset.rendered = "1";
    window.paypal.Buttons({
      style: { layout: "vertical", height: 55, label: "pay" },
      createOrder,
      onApprove: async () => { try { await onApproved(); } catch (e) { alertResult("stop", "Payment problem", e.message); } },
      onCancel: () => {},
      onError: (e) => alertResult("stop", "PayPal could not complete this", String(e)),
    }).render("#paypal-buttons");
  }

  async function demoPay() {
    $("#demo-pay").disabled = true;
    try { await createOrder(); await onApproved(); }
    catch (e) { alertResult("stop", "Payment problem", e.message); }
  }

  $("#cancel-before").addEventListener("click", async () => {
    try { await api(`/api/transfers/${transfer.id}/cancel`, { method: "POST" }); } catch (_) {}
    alertResult("stop", "Payment cancelled", "Nothing was sent and you were not charged.");
  });

  // --- step 4: result
  function alertResult(kind, title, text) {
    const b = $("#result-banner");
    b.className = `banner ${kind}`;
    b.innerHTML = `<h2>${escapeHtml(title)}</h2><p>${escapeHtml(text)}</p>`;
    $("#result-actions").innerHTML = "";
    show("step-result");
    speak(`${title}. ${text}`);
  }

  function renderResult() {
    const t = transfer;
    const who = t.payee.name;
    const amt = money(t.amount, t.currency);
    clearInterval(pollTimer);
    if (t.status === "released") {
      alertResult("ok", `Done. ${amt} sent to ${who}.`, t.family_decision === "approved" ? `${cfg.contact} checked and approved it.` : "Thank you.");
      return;
    }
    if (t.status === "cancelled") {
      alertResult("stop", "This payment was cancelled", t.family_decision === "declined"
        ? `${cfg.contact} stopped this payment to keep your money safe. You were not charged. ${t.family_note ? "Their note: " + t.family_note : ""}`
        : "Nothing was sent and you were not charged.");
      return;
    }
    if (t.status === "held") {
      const coolOff = t.decision === "cool_off";
      const when = t.release_at ? new Date(t.release_at * 1000).toLocaleString() : "";
      alertResult("warn",
        coolOff ? `Your payment is paused until ${when}` : `Your payment is on hold until ${cfg.contact} checks it`,
        `${t.message_to_payer || ""} ${coolOff ? `${cfg.contact} has been told. It will be sent automatically after the pause unless it is stopped.` : `We've asked ${cfg.contact} to look at it.`} Your money has not left your account.`);
      const actions = $("#result-actions");
      actions.innerHTML = `<button class="btn btn-secondary" id="stop-it" type="button">Cancel this payment</button>`;
      $("#stop-it").onclick = async () => { transfer = await api(`/api/transfers/${t.id}/cancel`, { method: "POST" }); renderResult(); };
      pollTimer = setInterval(async () => {
        const fresh = await api(`/api/transfers/${t.id}`);
        if (fresh.status !== "held") { transfer = fresh; renderResult(); }
      }, 3000);
      return;
    }
    alertResult("stop", "The payment did not go through", "PayPal did not authorise this payment. You were not charged.");
  }
})();
