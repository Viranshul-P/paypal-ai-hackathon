import { useCallback, useEffect, useState, type FormEvent } from 'react';

import { PinGate } from '../components/PinGate';
import { FamilyShell } from '../components/family/FamilyShell';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input, Label } from '../components/ui/Field';
import { Notice } from '../components/ui/Notice';
import { SwitchRow } from '../components/ui/SwitchRow';
import { api } from '../lib/api';
import { useConfig } from '../lib/config';
import type { Payee } from '../lib/types';

const ENGINE_NAMES: Record<string, string> = {
  M_pauseline_full: 'Rules, on-device model and LLM',
  F_pauseline: 'Rules and on-device model',
};

function statusRows(status: Record<string, string | number>) {
  const rows: [string, unknown][] = [
    ['PayPal', status.paypal],
    ['AI', status.ai],
    ['Risk engine', ENGINE_NAMES[String(status.engine)] ?? status.engine],
    ['Cooling-off', status.cooling_off_seconds === undefined ? undefined : `${status.cooling_off_seconds} seconds`],
    ['LLM checks since restart', status.llm_calls],
    ['Answers from cache', status.llm_cache_hits],
    ['Last LLM problem', status.llm_last_error],
  ];
  return rows.filter(([, value]) => value !== undefined);
}

function Panel() {
  const config = useConfig();
  const [payees, setPayees] = useState<Payee[]>([]);
  const [status, setStatus] = useState<Record<string, string | number>>({});
  const [error, setError] = useState('');
  const [resetting, setResetting] = useState(false);
  const [form, setForm] = useState({ name: '', relationship: '', email: '' });

  const load = useCallback(() => api<Payee[]>('/api/payees').then(setPayees, (e) => setError(e.message)), []);

  useEffect(() => {
    load();
    api<Record<string, string | number>>('/api/status').then(setStatus, () => undefined);
  }, [load]);

  async function update(id: string, field: 'known' | 'blocked', value: boolean) {
    setError('');
    try {
      await api(`/api/payees/${id}`, { method: 'PATCH', body: { [field]: value } });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That did not save. Try again.');
    }
  }

  async function add(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await api('/api/payees', { method: 'POST', body: { ...form, known: true } });
      setForm({ name: '', relationship: '', email: '' });
      await load();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'That did not save. Try again.');
    }
  }

  async function reset() {
    setResetting(true);
    setError('');
    try {
      await api('/api/demo/reset', { method: 'POST' });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not reset. Try again.');
    }
    setResetting(false);
  }

  return (
    <>
      <h1 className="text-[2.75rem] font-extrabold">Setup</h1>
      <p className="text-lg text-ink-2">
        Done once, by {config.contact_name} together with {config.payer_name}. Saved payees are people {config.payer_name} already pays.
      </p>
      {error && (
        <div className="mt-4">
          <Notice>{error}</Notice>
        </div>
      )}

      <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <section aria-labelledby="payees-h" className="space-y-4">
          <h2 id="payees-h" className="text-2xl font-extrabold">
            Payees
          </h2>
          {[...payees].sort((a, b) => a.name.localeCompare(b.name)).map((p) => (
            <Card key={p.id} className="space-y-2">
              <div>
                <p className="text-xl font-extrabold">{p.name}</p>
                {p.relationship && <p className="text-ink-2">{p.relationship}</p>}
                <p className="text-sm text-ink-2 [overflow-wrap:anywhere]">{p.email}</p>
              </div>
              <div className="divide-y divide-line">
                <SwitchRow label="Saved" hint={p.known ? 'Treated as known' : 'Treated as new'} checked={p.known} onChange={(v) => update(p.id, 'known', v)} />
                <SwitchRow label="Blocked" hint={p.blocked ? 'Payments are stopped' : 'Payments allowed'} checked={p.blocked} onChange={(v) => update(p.id, 'blocked', v)} />
              </div>
            </Card>
          ))}
        </section>

        <div className="space-y-5">
          <Card>
            <h2 className="text-2xl font-extrabold">Add a saved payee</h2>
            <form onSubmit={add} className="mt-3 space-y-3">
              <div>
                <Label htmlFor="n">Name</Label>
                <Input id="n" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="r">Relationship</Label>
                <Input id="r" placeholder="grandson, landlord, pharmacy" value={form.relationship} onChange={(e) => setForm({ ...form, relationship: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="e">PayPal email</Label>
                <Input id="e" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <Button type="submit">Add saved payee</Button>
            </form>
          </Card>

          <Card className="space-y-3">
            <h2 className="text-2xl font-extrabold">Demo</h2>
            <p className="text-ink-2">Resets the shared demo household and cancels any PayPal holds first.</p>
            <Button variant="secondary" className="ring-2 ring-line ring-inset" disabled={resetting} onClick={reset}>
              Reset demo
            </Button>
          </Card>

          <Card>
            <h2 className="text-2xl font-extrabold">System status</h2>
            <dl className="mt-2 space-y-1">
              {statusRows(status).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <dt className="text-ink-2">{k}</dt>
                  <dd className="text-right font-semibold">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>
      </div>
    </>
  );
}

export default function Setup() {
  return (
    <FamilyShell>
      <PinGate>
        <Panel />
      </PinGate>
    </FamilyShell>
  );
}
