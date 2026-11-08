const PIN_KEY = 'pauseline-pin';

// The family PIN lasts for this browser tab only, and storage can be unavailable.
let pin = '';
try {
  pin = sessionStorage.getItem(PIN_KEY) ?? '';
} catch {
  /* memory only */
}

export function getFamilyPin() {
  return pin;
}

export function setFamilyPin(value: string) {
  pin = value;
  try {
    if (value) sessionStorage.setItem(PIN_KEY, value);
    else sessionStorage.removeItem(PIN_KEY);
  } catch {
    /* memory only */
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

interface ApiOptions {
  method?: 'GET' | 'POST' | 'PATCH';
  body?: unknown;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const res = await fetch(path, {
    method: options.method ?? 'GET',
    headers: { 'Content-Type': 'application/json', ...(pin ? { 'X-Family-Pin': pin } : {}) },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  let data: any = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const detail = data?.detail ?? data?.error;
    const message = Array.isArray(detail) ? detail.map((d: { msg: string }) => d.msg).join('. ') : detail;
    throw new ApiError(message || `Request failed (${res.status})`, res.status);
  }
  return data as T;
}
