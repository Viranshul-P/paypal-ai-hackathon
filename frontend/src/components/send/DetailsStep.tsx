import clsx from 'clsx';
import { Mic, UserPlus } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { api } from '../../lib/api';
import { useConfig } from '../../lib/config';
import { useI18n } from '../../lib/i18n';
import type { Payee } from '../../lib/types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Input, Label, Textarea } from '../ui/Field';
import { Notice } from '../ui/Notice';

export const NEW_PAYEE = '__new__';

export interface Details {
  payeeId: string;
  amount: number;
  statement: string;
  newName: string;
  newEmail: string;
}

interface DetailsStepProps {
  payees: Payee[];
  busy: boolean;
  error: string;
  onError: (message: string) => void;
  onContinue: (details: Details) => void;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

// One-click examples for trying the app: /send?demo=normal or /send?demo=scam
const DEMOS: Record<string, { payee: string; amount: string; statement: string }> = {
  normal: { payee: 'Rahul', amount: '80', statement: "Rahul's college books" },
  scam: {
    payee: 'Safe Account Services',
    amount: '3000',
    statement: 'The bank officer said my account is hacked, I must move my savings to a safe account, he is still on the phone',
  },
};

export function DetailsStep({ payees, busy, error, onError, onContinue }: DetailsStepProps) {
  const { t, lang } = useI18n();
  const config = useConfig();
  const [payeeId, setPayeeId] = useState('');
  const [amount, setAmount] = useState('');
  const [statement, setStatement] = useState('');
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [listening, setListening] = useState(false);
  const recognition = useRef<any>(null);

  const [params] = useSearchParams();
  const demo = DEMOS[params.get('demo') ?? ''];
  const demoApplied = useRef(false);
  useEffect(() => {
    if (!demo || demoApplied.current || !payees.length) return;
    const p = payees.find((x) => x.name === demo.payee);
    if (!p) return;
    demoApplied.current = true;
    setPayeeId(p.id);
    setAmount(demo.amount);
    setStatement(demo.statement);
  }, [demo, payees]);

  // A message about the form goes away as soon as the person changes anything.
  useEffect(() => {
    onError('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payeeId, amount, statement, newName, newEmail]);

  const Speech = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  function toggleVoice() {
    if (!Speech) return;
    if (recognition.current) {
      recognition.current.stop();
      return;
    }
    const rec = new Speech();
    rec.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    rec.interimResults = true;
    const base = statement ? `${statement} ` : '';
    let spoken = base;
    rec.onresult = (e: any) => {
      spoken = base + Array.from(e.results as ArrayLike<any>).map((r) => r[0].transcript).join(' ');
      setStatement(spoken);
    };
    rec.onerror = (e: any) => {
      if (e.error === 'not-allowed') {
        onError(t('Allow the microphone in your browser to speak, or type instead.', 'बोलने के लिए ब्राउज़र में माइक्रोफ़ोन की अनुमति दें, या लिखकर बताएं।'));
      }
    };
    rec.onend = async () => {
      setListening(false);
      recognition.current = null;
      try {
        const intent = await api<{ amount: number | null; payee: Payee | null }>('/api/intent', { method: 'POST', body: { text: spoken } });
        if (intent.amount) setAmount((a) => a || String(intent.amount));
        if (intent.payee) setPayeeId((p) => p || intent.payee!.id);
      } catch {
        /* filling these in from speech is optional */
      }
    };
    recognition.current = rec;
    setListening(true);
    rec.start();
  }

  function submit() {
    const value = parseFloat(amount);
    const words = statement.trim();
    if (!payeeId) return onError(t('Please choose who you are paying.', 'कृपया चुनें कि पैसे किसे भेजने हैं।'));
    if (payeeId === NEW_PAYEE && !newName.trim()) return onError(t('Please enter their name.', 'कृपया उनका नाम लिखें।'));
    if (payeeId === NEW_PAYEE && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(newEmail.trim())) {
      return onError(t('Please enter their PayPal email, like name@example.com.', 'कृपया उनका PayPal ईमेल लिखें, जैसे name@example.com'));
    }
    if (!(value > 0)) return onError(t('Please enter an amount.', 'कृपया रकम लिखें।'));
    if (!words) return onError(t('Please tell us, in a few words, what the payment is for.', 'कृपया थोड़े शब्दों में बताएं कि यह पैसे किसलिए हैं।'));
    onContinue({ payeeId, amount: value, statement: words, newName: newName.trim(), newEmail: newEmail.trim() });
  }

  const visible = payees.filter((p) => !p.blocked);

  return (
    <div className="space-y-3">
      <h1 className="px-1 text-[2.2rem] font-extrabold">{t(`Who are you paying, ${config.payer_name}?`, `${config.payer_name}, आप किसे पैसे भेज रहे हैं?`)}</h1>

      <Card className="p-3">
        <div role="group" aria-label={t('Choose who to pay', 'चुनें किसे भेजना है')} className="space-y-1">
          {visible.map((p) => (
            <PayeeRow
              key={p.id}
              selected={payeeId === p.id}
              onClick={() => setPayeeId(p.id)}
              title={p.name}
              subtitle={p.relationship || (p.known ? t('Saved', 'सेव किया हुआ') : t('New to you', 'आपके लिए नया'))}
              badge={initials(p.name)}
            />
          ))}
          <PayeeRow
            selected={payeeId === NEW_PAYEE}
            onClick={() => setPayeeId(NEW_PAYEE)}
            title={t('Someone new', 'कोई नया व्यक्ति')}
            subtitle={t('Add a name and email', 'नाम और ईमेल जोड़ें')}
            badge={<UserPlus className="size-5" aria-hidden />}
          />
        </div>
        {payeeId === NEW_PAYEE && (
          <div className="mt-3 space-y-3 px-2 pb-2">
            <div>
              <Label htmlFor="np-name">{t('Their name', 'उनका नाम')}</Label>
              <Input id="np-name" value={newName} onChange={(e) => setNewName(e.target.value)} autoComplete="off" />
            </div>
            <div>
              <Label htmlFor="np-email">{t('Their PayPal email', 'उनका PayPal ईमेल')}</Label>
              <Input id="np-email" type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} autoComplete="off" />
            </div>
          </div>
        )}
      </Card>

      <Card className="space-y-4">
        <div>
          <Label htmlFor="amount">
            {t('Amount', 'रकम')} ({config.currency})
          </Label>
          <input
            id="amount"
            type="number"
            inputMode="decimal"
            min="1"
            step="0.01"
            placeholder="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="tabular w-full border-0 bg-transparent p-0 text-[3.2rem] leading-none font-extrabold text-ink placeholder:text-ink-2/70 focus:outline-none"
          />
        </div>
        <div>
          <Label htmlFor="statement">{t('What is it for? Say it in your own words.', 'यह किसलिए है? अपने शब्दों में बताएं।')}</Label>
          <Textarea
            id="statement"
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            placeholder={t("For example: Rahul's college books", 'जैसे: राहुल की कॉलेज की किताबें')}
          />
          <button
            type="button"
            onClick={toggleVoice}
            disabled={!Speech}
            aria-pressed={listening}
            title={Speech ? undefined : 'Speech input needs Chrome or Edge'}
            className={clsx(
              'mt-2 flex min-h-13 w-full items-center justify-center gap-2 rounded-full font-semibold disabled:opacity-50',
              listening ? 'bg-action text-white' : 'bg-action-soft text-action',
            )}
          >
            <Mic className="size-5" aria-hidden />
            {listening ? t('Listening. Tap to stop', 'सुन रहे हैं। रोकने के लिए दबाएं') : t('Speak instead', 'बोलकर बताएं')}
          </button>
        </div>
      </Card>

      {error && <Notice>{error}</Notice>}
      <Button onClick={submit} disabled={busy}>
        {busy ? t('Checking', 'जांच हो रही है') : t('Continue', 'आगे बढ़ें')}
      </Button>
    </div>
  );
}

interface PayeeRowProps {
  selected: boolean;
  onClick: () => void;
  title: string;
  subtitle: string;
  badge: React.ReactNode;
}

function PayeeRow({ selected, onClick, title, subtitle, badge }: PayeeRowProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={clsx(
        'flex min-h-16 w-full items-center gap-3 rounded-2xl p-2 text-left transition-colors duration-150',
        selected ? 'bg-action-soft' : 'hover:bg-tint',
      )}
    >
      <span className={clsx('flex size-12 shrink-0 items-center justify-center rounded-full font-extrabold', selected ? 'bg-action text-white' : 'bg-tint text-ink-2')}>
        {badge}
      </span>
      <span className="min-w-0">
        <span className="block truncate text-lg leading-tight font-semibold">{title}</span>
        <span className="block text-ink-2">{subtitle}</span>
      </span>
    </button>
  );
}
