import { Check, X } from 'lucide-react';
import { useEffect } from 'react';
import { Link } from 'react-router-dom';

import { useConfig } from '../../lib/config';
import { money, speak } from '../../lib/format';
import { useI18n } from '../../lib/i18n';
import type { Transfer } from '../../lib/types';
import { PauseMark } from '../Brand';
import { Button, buttonClass } from '../ui/Button';
import { Card } from '../ui/Card';
import { StatusTag } from '../ui/StatusTag';

export type Tone = 'held' | 'sent' | 'stop';

export interface Outcome {
  tone: Tone;
  title: string;
  text: string;
}

export function useOutcome() {
  const { t } = useI18n();
  const config = useConfig();
  const contact = config.contact_name;

  return (tr: Transfer): Outcome => {
    const who = tr.payee.name;
    const amt = money(tr.amount, tr.currency);
    const uncharged = t('Nothing was sent and you were not charged.', 'कुछ नहीं भेजा गया और आपसे कोई पैसा नहीं लिया गया।');

    if (tr.status === 'released' && tr.delivery_failed) {
      return {
        tone: 'held',
        title: t(`${amt} was taken, but ${who} has not received it yet`, `${amt} लिए गए, पर ${who} को अभी नहीं मिले`),
        text: t(`PayPal did not accept the transfer to ${who}. Please ask ${contact} to check it.`, `PayPal ने ${who} को भेजना स्वीकार नहीं किया। कृपया ${contact} से जांच करवाएं।`),
      };
    }
    if (tr.status === 'released') {
      return {
        tone: 'sent',
        title: t(`${amt} sent to ${who}`, `${who} को ${amt} भेजे गए`),
        text: tr.family_decision === 'approved' ? t(`${contact} checked and approved it.`, `${contact} ने जांच कर इसे मंज़ूरी दी।`) : t('All done. Thank you.', 'हो गया। धन्यवाद।'),
      };
    }
    if (tr.status === 'cancelled') {
      const note = tr.family_note ? t(` Their note: ${tr.family_note}`, ` उनका संदेश: ${tr.family_note}`) : '';
      return {
        tone: 'stop',
        title: t('This payment was cancelled', 'यह पेमेंट रद्द हो गया'),
        text: tr.family_decision === 'declined'
          ? t(`${contact} stopped this payment to keep your money safe. You were not charged.${note}`, `आपके पैसे सुरक्षित रखने के लिए ${contact} ने यह पेमेंट रोक दिया। आपसे कोई पैसा नहीं लिया गया।${note}`)
          : uncharged,
      };
    }
    if (tr.status === 'held') {
      const coolOff = tr.decision === 'cool_off';
      const when = tr.release_at ? new Date(tr.release_at * 1000).toLocaleString() : '';
      const next = coolOff
        ? t(`It will be sent after the pause unless ${contact} stops it.`, `रुकने के बाद यह भेज दिया जाएगा, जब तक ${contact} इसे न रोकें।`)
        : t(`${contact} can already see this and will decide. Please call ${contact} too.`, `${contact} इसे देख सकती हैं और फ़ैसला करेंगी। कृपया ${contact} को फ़ोन भी करें।`);
      return {
        tone: 'held',
        title: coolOff ? t(`Paused until ${when}`, `${when} तक रुका है`) : t(`We paused this, ${config.payer_name}`, `${config.payer_name}, हमने इसे रोक दिया है`),
        text: `${tr.message_to_payer || ''} ${next} ${t('Your money has not left your account.', 'आपके पैसे आपके खाते से नहीं गए हैं।')}`.trim(),
      };
    }
    return {
      tone: 'stop',
      title: t('The payment did not go through', 'पेमेंट पूरा नहीं हुआ'),
      text: t('PayPal did not authorise this payment. You were not charged.', 'PayPal ने इस पेमेंट की अनुमति नहीं दी। आपसे कोई पैसा नहीं लिया गया।'),
    };
  };
}

const MARK_STYLE: Record<Tone, string> = {
  held: 'bg-card text-held',
  sent: 'bg-card text-sent',
  stop: 'bg-card text-stop',
};

function OutcomeMark({ tone }: { tone: Tone }) {
  return (
    <div
      className={`flex size-16 shrink-0 items-center justify-center rounded-full ${MARK_STYLE[tone]}`}
    >
      {tone === 'held' && <PauseMark className="h-7" />}
      {tone === 'sent' && <Check className="size-9" strokeWidth={3} aria-hidden />}
      {tone === 'stop' && <X className="size-9" strokeWidth={3} aria-hidden />}
    </div>
  );
}

interface ResultStepProps {
  transfer: Transfer;
  outcome: Outcome;
  onCancel: () => void;
}

export function ResultStep({ transfer: tr, outcome, onCancel }: ResultStepProps) {
  const { t } = useI18n();

  useEffect(() => {
    speak(`${outcome.title}. ${outcome.text}`);
  }, [outcome.title, outcome.text]);

  return (
    <div className="space-y-3" aria-live="polite">
      <div className="flex items-center gap-3 px-1">
        <OutcomeMark tone={outcome.tone} />
        <h1 className="min-w-0 flex-1 text-[2.05rem] font-extrabold">{outcome.title}</h1>
      </div>

      <Card>
        <div className="flex items-start justify-between gap-3">
          <p className="tabular text-[2.6rem] leading-none font-extrabold">{money(tr.amount, tr.currency)}</p>
          <StatusTag transfer={tr} />
        </div>
        <p className="mt-1 text-lg font-semibold text-ink-2">
          {t('to', 'पाने वाले:')} {tr.payee.name}
        </p>
      </Card>

      <Card>
        <p className="text-lg leading-snug">{outcome.text}</p>
      </Card>

      {tr.status === 'held' && <Button onClick={onCancel}>{t('Cancel this payment', 'यह पेमेंट रद्द करें')}</Button>}
      {tr.status === 'held' ? (
        <Link to="/" className={buttonClass('secondary')}>
          {t('Back to home', 'होम पर वापस जाएं')}
        </Link>
      ) : (
        <Link to="/send" reloadDocument className={buttonClass('secondary')}>
          {t('Make another payment', 'एक और पेमेंट करें')}
        </Link>
      )}
    </div>
  );
}
