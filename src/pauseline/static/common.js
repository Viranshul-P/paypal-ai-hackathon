// Small shared helpers. No framework: pages stay fast on old phones.
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// --- storage that survives private windows and blocked site data
function stored(area, key, fallback = "") {
  try { return window[area].getItem(key) ?? fallback; } catch (_) { return fallback; }
}
function store(area, key, value) {
  try { value ? window[area].setItem(key, value) : window[area].removeItem(key); } catch (_) { /* memory only */ }
}

// --- the family PIN lasts for this browser tab only
let _pin = stored("sessionStorage", "pauseline-pin");
function setFamilyPin(pin) { _pin = pin; store("sessionStorage", "pauseline-pin", pin); }

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(_pin ? { "X-Family-Pin": _pin } : {}) },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) {
    const detail = data && (data.detail || data.error);
    const msg = Array.isArray(detail) ? detail.map((d) => d.msg).join(". ") : detail;
    const err = new Error(msg || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

// Family view and Setup: show the PIN screen until the right PIN is entered.
async function requireFamily(onReady) {
  const lock = $("#lock");
  const content = $("#family-content");
  const open = () => { lock.classList.add("hidden"); content.classList.remove("hidden"); onReady(); };
  const pinIsRight = async () => {
    try { await api("/api/family/overview"); return true; }
    catch (e) { if (e.status === 401) return false; throw e; }
  };
  if (_pin) {
    try { if (await pinIsRight()) return open(); } catch (_) { /* show the PIN screen */ }
    setFamilyPin("");
  }
  lock.classList.remove("hidden");
  $("#pin").focus();
  $("#lock-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("#lock-error");
    err.classList.add("hidden");
    setFamilyPin($("#pin").value.trim());
    try {
      if (await pinIsRight()) return open();
      setFamilyPin("");
      err.textContent = "That PIN is not right. Check it and try again.";
    } catch (ex) {
      setFamilyPin("");
      err.textContent = ex.message;
    }
    err.classList.remove("hidden");
    $("#pin").value = "";
    $("#pin").focus();
  });
}

// --- English / Hindi. Elements carry their Hindi in data-hi; dynamic text uses T(en, hi).
let LANG = stored("localStorage", "pauseline-lang", "en");
const T = (en, hi) => (LANG === "hi" ? hi : en);

function applyLang() {
  document.documentElement.lang = LANG;
  $$("[data-hi]").forEach((el) => {
    if (el.dataset.en === undefined) el.dataset.en = el.textContent;
    el.textContent = LANG === "hi" ? el.dataset.hi : el.dataset.en;
  });
  $$("[data-hi-placeholder]").forEach((el) => {
    if (el.dataset.enPlaceholder === undefined) el.dataset.enPlaceholder = el.placeholder;
    el.placeholder = LANG === "hi" ? el.dataset.hiPlaceholder : el.dataset.enPlaceholder;
  });
  const toggle = $("#lang-toggle");
  if (toggle) toggle.textContent = LANG === "hi" ? "English" : "हिन्दी";
  document.dispatchEvent(new CustomEvent("langchange"));
}

document.addEventListener("DOMContentLoaded", () => {
  $("#lang-toggle")?.addEventListener("click", () => {
    LANG = LANG === "hi" ? "en" : "hi";
    store("localStorage", "pauseline-lang", LANG);
    applyLang();
  });
  applyLang();
});

function money(amount, currency) {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
  } catch (_) {
    return `${amount} ${currency}`;
  }
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function speak(text, lang) {
  if (!("speechSynthesis" in window) || !text) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang || (/[ऀ-ॿ]/.test(text) ? "hi-IN" : "en-IN");
  u.rate = 0.9;
  window.speechSynthesis.speak(u);
}

function timeAgo(epochSeconds) {
  const s = Math.max(0, Math.round(Date.now() / 1000 - epochSeconds));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

const STATUS_LABEL = {
  draft: "Being checked",
  awaiting_payer: "Waiting for PayPal",
  held: "On hold",
  released: "Sent",
  cancelled: "Cancelled",
  failed: "Failed",
};
