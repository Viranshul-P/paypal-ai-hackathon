import { useState } from 'react';

import { useConfig } from '../../lib/config';
import { money } from '../../lib/format';
import type { Signal, Transfer } from '../../lib/types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Input, Label } from '../ui/Field';
import { Notice } from '../ui/Notice';
import { StatusTag } from '../ui/StatusTag';

const SCAM_LABEL: Record<string, string> = {
  bank_safe_account: "Fake bank or 'safe account'",
  digital_arrest_or_government: "Fake police or government ('digital arrest')",
  family_emergency: 'Fake family emergency',
  tech_support: 'Fake tech support',
  romance: 'Romance scam',
  prize_or_lottery: 'Prize or lottery fee',
  investment_or_crypto: 'Investment or crypto',
  fake_invoice_or_refund: 'Fake refund or invoice',
  job_or_task: 'Job or task scam',
  other: 'Other warning signs',
};

function Chips({ items }: { items: string[] }) {
  return (
    <ul className="mt-1.5 flex list-none flex-wrap gap-1.5 p-0">
      {items.map((item) => (
        <li key={item} className="rounded-xl bg-tint px-3 py-1">
          {item}
        </li>
      ))}
    </ul>
  );
}

function reason(s: Signal) {
  return s.name === 'ai_flag' ? s.evidence : s.label;
}

interface HoldCardProps {
  transfer: Transfer;
  onDecide: (id: string, approve: boolean, note: string) => Promise<void>;
}

export function HoldCard({ transfer: t, onDecide }: HoldCardProps) {
  const config = useConfig();
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const coolOff = t.decision === 'cool_off';

  async function decide(approve: boolean) {
    setBusy(true);
    setError('');
    try {
      await onDecide(t.id, approve, note);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That did not work. Try again.');
      setBusy(false);
    }
  }

  // The fallback summary only repeats what is listed below; a written one from the LLM adds something.
  const aiSummary = t.summary_for_family.startsWith('A payment of') ? '' : t.summary_for_family;
  const answers = Object.entries(t.answers ?? {}).map(([q, a]) => `${q.replaceAll('_', ' ')}: ${a}`);

  return (
    <Card className="space-y-4 p-6 ring-4 ring-held-ground">
      <div>
        <div className="flex items-start justify-between gap-3">
          <p className="tabular text-4xl font-extrabold">{money(t.amount, t.currency)}</p>
          <StatusTag transfer={t} />
        </div>
        <p className="text-lg font-semibold text-ink-2">
          to {t.payee.name}
          {t.payee.known ? '' : ' (new payee)'}
        </p>
      </div>

      <div>
        <h3 className="text-2xl font-extrabold">{SCAM_LABEL[t.scam_type ?? ''] ?? 'Warning signs'}</h3>
        <p className="mt-1 text-ink-2">
          Risk {Math.round((t.risk ?? 0) * 100)}%.{' '}
          {coolOff && t.release_at
            ? `Sends automatically on ${new Date(t.release_at * 1000).toLocaleString()} unless you decline.`
            : 'Will not be sent unless you approve.'}{' '}
          {config.payer_name} has not been charged.
        </p>
      </div>

      <div>
        <Label htmlFor={`note-${t.id}`}>Note to {config.payer_name} (optional)</Label>
        <Input id={`note-${t.id}`} value={note} onChange={(e) => setNote(e.target.value)} placeholder="I'll call you in a minute, Ma" />
      </div>

      {error && <Notice>{error}</Notice>}

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button disabled={busy} onClick={() => decide(false)}>
          Decline and cancel
        </Button>
        <Button variant="secondary" disabled={busy} className="ring-2 ring-line ring-inset" onClick={() => decide(true)}>
          It's genuine, release it
        </Button>
      </div>

      <div>
        <p className="font-semibold text-ink-2">{config.payer_name}'s words</p>
        <p className="mt-1 rounded-2xl bg-tint px-4 py-3 text-lg">{t.statement}</p>
      </div>

      {aiSummary && (
        <div>
          <p className="font-semibold text-ink-2">AI summary</p>
          <p className="mt-1">{aiSummary}</p>
        </div>
      )}

      {t.signals.length > 0 && (
        <div>
          <p className="font-semibold text-ink-2">Why it was paused</p>
          <Chips items={[...new Set(t.signals.map(reason))]} />
        </div>
      )}

      {answers.length > 0 && (
        <div>
          <p className="font-semibold text-ink-2">{config.payer_name}'s answers</p>
          <Chips items={answers} />
        </div>
      )}
    </Card>
  );
}
