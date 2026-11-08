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
    $("#details-error").classList.add("hidden");
  }));
  ["#amount", "#statement", "#np-name", "#np-email"].forEach((s) => $(s).addEventListener("input", () => $("#details-error").classList.add("hidden")));

  // --- speech input (Web Speech API; Chrome / Edge)
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = $("#mic");
  if (!SR) { mic.disabled = true; mic.title = "Speech input needs Chrome or Edge"; }
  document.addEventListener("langchange", () => { $("#mic-lang").value = LANG === "hi" ? "hi-IN" : "en-IN"; });
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
    rec.onerror = (e) => {
      if (e.error === "not-allowed") fail($("#details-error"), T("Allow the microphone in your browser to speak, or type instead.", "बोलने के लिए ब्राउज़र में माइक्रोफ़ोन की अनुमति दें, या लिखकर बताएं।"));
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
  let newPayeeCreated = null;  // so that retrying after an error does not add the same person twice

  $("#continue").addEventListener("click", async () => {
    const err = $("#details-error"); err.classList.add("hidden");
    const amount = parseFloat($("#amount").value);
    const statement = $("#statement").value.trim();
    if (!payeeId) return fail(err, T("Please choose who you are paying.", "कृपया चुनें कि पैसे किसे भेजने हैं।"));
    if (!(amount > 0)) return fail(err, T("Please enter an amount.", "कृपया रकम लिखें।"));
    if (!statement) return fail(err, T("Please tell us, in a few words, what the payment is for.", "कृपया थोड़े शब्दों में बताएं कि यह पैसे किसलिए हैं।"));
    let pid = payeeId;
    if (pid === "__new__") {
      const name = $("#np-name").value.trim();
      const email = $("#np-email").value.trim();
      if (!name) return fail(err, T("Please enter their name.", "कृपया उनका नाम लिखें।"));
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail(err, T("Please enter their PayPal email, like name@example.com.", "कृपया उनका PayPal ईमेल लिखें, जैसे name@example.com"));
    }
    $("#continue").disabled = true;
    try {
      if (pid === "__new__") {
        const name = $("#np-name").value.trim();
        const email = $("#np-email").value.trim();
        if (!newPayeeCreated || newPayeeCreated.name !== name || newPayeeCreated.email !== email) {
          newPayeeCreated = await api("/api/payees", { method: "POST", body: { name, email, known: false } });
        }
        pid = newPayeeCreated.id;
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
    const qs = transfer.questions.map((q) => ({ ...q, shown: LANG === "hi" ? q.text_hi : q.text }));
    $("#questions-title").textContent = qs.length === 1
      ? T("One quick question", "एक छोटा सवाल")
      : T(`${qs.length} quick questions`, `${qs.length} छोटे सवाल`);
    const box = $("#questions");
    box.innerHTML = qs.map((q) => `
      <div class="question slip" data-q="${escapeHtml(q.id)}">
        <p>${escapeHtml(q.shown)}</p>
        <div class="btn-row">
          <button type="button" class="btn btn-secondary choice" data-a="yes" aria-pressed="false">${T("Yes", "हां")}</button>
          <button type="button" class="btn btn-secondary choice" data-a="no" aria-pressed="false">${T("No", "नहीं")}</button>
        </div>
      </div>`).join("");
    $("#answers-continue").disabled = true;
    $$(".question", box).forEach((qel) => {
      $$(".choice", qel).forEach((b) => b.addEventListener("click", () => {
        $$(".choice", qel).forEach((x) => x.setAttribute("aria-pressed", "false"));
        b.setAttribute("aria-pressed", "true");
        answers[qel.dataset.q] = b.dataset.a;
        $("#answers-continue").disabled = Object.keys(answers).length < qs.length;
      }));
    });
    show("step-questions");
    speak(qs[0].shown);
  }

  $("#answers-continue").addEventListener("click", async () => {
    $("#answers-continue").disabled = true;
    try {
      transfer = await api(`/api/transfers/${transfer.id}/answers`, { method: "POST", body: { answers } });
      toPay();
    } catch (e) {
      alertResult("stop", T("We could not save your answers", "आपके जवाब सेव नहीं हुए"), e.message);
    }
  });

  // --- step 3: pay
  function toPay() {
    const t = transfer;
    $("#pay-title").textContent = T(`Pay ${money(t.amount, t.currency)} to ${t.payee.name}`, `${t.payee.name} को ${money(t.amount, t.currency)} भेजें`);
    const notice = $("#pay-notice");
    if (t.decision && t.decision !== "allow") {
      notice.innerHTML = `<h2>${T("We will hold this payment for a check", "हम जांच के लिए इस पेमेंट को रोकेंगे")}</h2><p>${escapeHtml(t.message_to_payer)}</p>`;
      notice.classList.remove("hidden");
      speak(t.message_to_payer);
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
    if (!window.paypal) {
      alertResult("stop", T("PayPal did not load", "PayPal लोड नहीं हुआ"), T("Check your internet connection, then reload this page and try again. You have not been charged.", "इंटरनेट जांचें, फिर यह पेज दोबारा खोलकर कोशिश करें। आपसे कोई पैसा नहीं लिया गया है।"));
      return;
    }
    el.dataset.rendered = "1";
    window.paypal.Buttons({
      style: { layout: "vertical", height: 55, label: "pay" },
      createOrder,
      onApprove: async () => { try { await onApproved(); } catch (e) { alertResult("stop", T("Payment problem", "पेमेंट में समस्या"), e.message); } },
      onCancel: () => {},
      onError: (e) => alertResult("stop", T("PayPal could not complete this", "PayPal यह पूरा नहीं कर सका"), String(e)),
    }).render("#paypal-buttons");
  }

  async function demoPay() {
    $("#demo-pay").disabled = true;
    try { await createOrder(); await onApproved(); }
    catch (e) { alertResult("stop", T("Payment problem", "पेमेंट में समस्या"), e.message); }
  }

  $("#cancel-before").addEventListener("click", async () => {
    try { await api(`/api/transfers/${transfer.id}/cancel`, { method: "POST" }); } catch (_) {}
    alertResult("stop", T("Payment cancelled", "पेमेंट रद्द किया गया"), T("Nothing was sent and you were not charged.", "कुछ नहीं भेजा गया और आपसे कोई पैसा नहीं लिया गया।"), T("Cancelled", "रद्द"));
  });

  // --- step 4: result
  const STAMP = { ok: () => T("Sent", "भेजा गया"), warn: () => T("On hold", "रोका गया"), stop: () => T("Not sent", "नहीं भेजा") };

  function alertResult(kind, title, text, stamp) {
    const b = $("#result-banner");
    b.className = `banner result-banner ${kind}`;
    b.innerHTML = `<span class="stamp ${kind}">${escapeHtml(stamp || STAMP[kind]())}</span><h2>${escapeHtml(title)}</h2><p>${escapeHtml(text)}</p>`;
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
      if (t.delivery_failed) {
        alertResult("warn", T(`${amt} was taken, but ${who} has not received it yet`, `${amt} लिए गए, पर ${who} को अभी नहीं मिले`),
          T(`PayPal did not accept the transfer to ${who}. Please ask ${cfg.contact} to check it.`, `PayPal ने ${who} को भेजना स्वीकार नहीं किया। कृपया ${cfg.contact} से जांच करवाएं।`), T("Check needed", "जांच ज़रूरी"));
        return;
      }
      alertResult("ok", T(`${amt} sent to ${who}.`, `${who} को ${amt} भेजे गए।`), t.family_decision === "approved" ? T(`${cfg.contact} checked and approved it.`, `${cfg.contact} ने जांच कर इसे मंज़ूरी दी।`) : T("Thank you.", "धन्यवाद।"));
      return;
    }
    if (t.status === "cancelled") {
      alertResult("stop", T("This payment was cancelled", "यह पेमेंट रद्द हो गया"), t.family_decision === "declined"
        ? T(`${cfg.contact} stopped this payment to keep your money safe. You were not charged. ${t.family_note ? "Their note: " + t.family_note : ""}`, `आपके पैसे सुरक्षित रखने के लिए ${cfg.contact} ने यह पेमेंट रोक दिया। आपसे कोई पैसा नहीं लिया गया। ${t.family_note ? "उनका संदेश: " + t.family_note : ""}`)
        : T("Nothing was sent and you were not charged.", "कुछ नहीं भेजा गया और आपसे कोई पैसा नहीं लिया गया।"), T("Cancelled", "रद्द"));
      return;
    }
    if (t.status === "held") {
      const coolOff = t.decision === "cool_off";
      const when = t.release_at ? new Date(t.release_at * 1000).toLocaleString() : "";
      const next = coolOff
        ? T(`It is waiting in ${cfg.contact}'s Family view, and will be sent after the pause unless it is stopped.`, `यह ${cfg.contact} के फ़ैमिली व्यू में है, और रुकने के बाद अपने आप भेज दिया जाएगा, जब तक इसे रोका न जाए।`)
        : T(`It is waiting in ${cfg.contact}'s Family view. Please call ${cfg.contact} yourself.`, `यह ${cfg.contact} के फ़ैमिली व्यू में है। कृपया खुद ${cfg.contact} को फ़ोन करें।`);
      alertResult("warn",
        coolOff ? T(`Your payment is paused until ${when}`, `आपका पेमेंट ${when} तक रुका है`) : T(`Your payment is on hold until ${cfg.contact} checks it`, `${cfg.contact} की जांच तक आपका पेमेंट रुका है`),
        `${t.message_to_payer || ""} ${next} ${T("Your money has not left your account.", "आपके पैसे आपके खाते से नहीं गए हैं।")}`);
      const actions = $("#result-actions");
      actions.innerHTML = `<button class="btn btn-secondary" id="stop-it" type="button">${T("Cancel this payment", "यह पेमेंट रद्द करें")}</button>`;
      $("#stop-it").onclick = async () => { transfer = await api(`/api/transfers/${t.id}/cancel`, { method: "POST" }); renderResult(); };
      pollTimer = setInterval(async () => {
        try {
          const fresh = await api(`/api/transfers/${t.id}`);
          if (fresh.status !== "held") { transfer = fresh; renderResult(); }
        } catch (_) { /* try again on the next tick */ }
      }, 3000);
      return;
    }
    alertResult("stop", T("The payment did not go through", "पेमेंट पूरा नहीं हुआ"), T("PayPal did not authorise this payment. You were not charged.", "PayPal ने इस पेमेंट की अनुमति नहीं दी। आपसे कोई पैसा नहीं लिया गया।"));
  }
})();
