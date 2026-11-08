import { useEffect, useRef, useState } from 'react';

import { useConfig } from '../../lib/config';
import { money } from '../../lib/format';
import { useI18n } from '../../lib/i18n';
import type { Transfer } from '../../lib/types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Notice } from '../ui/Notice';

interface PayPalButtonsProps {
  createOrder: () => Promise<string>;
  onApproved: () => Promise<void>;
  onFailure: (message: string) => void;
}

function PayPalButtons({ createOrder, onApproved, onFailure }: PayPalButtonsProps) {
  const config = useConfig();
  const { t } = useI18n();
  const box = useRef<HTMLDivElement>(null);
  const handlers = useRef({ createOrder, onApproved, onFailure });
  handlers.current = { createOrder, onApproved, onFailure };

  useEffect(() => {
    const unavailable = t('PayPal did not load. Check your internet connection, then try again. You have not been charged.', 'PayPal लोड नहीं हुआ। इंटरनेट जांचकर फिर कोशिश करें। आपसे कोई पैसा नहीं लिया गया है।');
    let cancelled = false;
    const render = () => {
      const paypal = (window as any).paypal;
      if (cancelled || !box.current) return;
      if (!paypal) return handlers.current.onFailure(unavailable);
      box.current.innerHTML = '';
      paypal
        .Buttons({
          style: { layout: 'vertical', height: 55, label: 'pay', shape: 'pill' },
          createOrder: () => handlers.current.createOrder(),
          onApprove: () => handlers.current.onApproved(),
          onError: (e: unknown) => handlers.current.onFailure(String(e)),
        })
        .render(box.current);
    };

    const id = 'paypal-sdk';
    const existing = document.getElementById(id) as HTMLScriptElement | null;
    if ((window as any).paypal) render();
    else if (existing) existing.addEventListener('load', render);
    else {
      const script = document.createElement('script');
      script.id = id;
      script.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(config.paypal_client_id)}&currency=${config.currency}&intent=authorize&components=buttons`;
      script.onload = render;
      script.onerror = () => handlers.current.onFailure(unavailable);
      document.head.appendChild(script);
    }
    return () => {
      cancelled = true;
    };
    // The SDK is loaded once; handlers stay current through the ref.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={box} className="min-h-14" data-testid="paypal-buttons" />;
}

interface PayStepProps {
  transfer: Transfer;
  error: string;
  createOrder: () => Promise<string>;
  onApproved: () => Promise<void>;
  onFailure: (message: string) => void;
  onCancel: () => void;
}

export function PayStep({ transfer: tr, error, createOrder, onApproved, onFailure, onCancel }: PayStepProps) {
  const { t } = useI18n();
  const config = useConfig();
  const [demoBusy, setDemoBusy] = useState(false);
  const warned = tr.decision !== null && tr.decision !== 'allow';

  async function demoPay() {
    setDemoBusy(true);
    try {
      await createOrder();
      await onApproved();
    } catch (e) {
      onFailure(e instanceof Error ? e.message : t('Payment problem', 'पेमेंट में समस्या'));
      setDemoBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <Card>
        <p className="tabular text-[3.2rem] leading-none font-extrabold">{money(tr.amount, tr.currency)}</p>
        <p className="mt-1 text-xl font-semibold text-ink-2">
          {t('to', 'पाने वाले:')} {tr.payee.name}
        </p>
      </Card>

      {warned && (
        <div className="rounded-card bg-held-soft p-5 text-held">
          <h2 className="text-2xl font-extrabold">{t('We will hold this payment for a check', 'हम जांच के लिए इस पेमेंट को रोकेंगे')}</h2>
          <p className="mt-1 text-lg">{tr.message_to_payer}</p>
        </div>
      )}

      <Card className="space-y-3">
        <p className="text-lg">{t('PayPal holds your money until the payment is confirmed. If anything looks wrong, you are not charged.', 'पेमेंट पक्का होने तक PayPal आपके पैसे रोककर रखता है। कुछ गड़बड़ लगे तो आपसे पैसा नहीं कटता।')}</p>
        {config.paypal_live ? (
          <PayPalButtons createOrder={createOrder} onApproved={onApproved} onFailure={onFailure} />
        ) : (
          <>
            <Button onClick={demoPay} disabled={demoBusy}>
              {t('Pay with PayPal (demo)', 'PayPal से भुगतान (डेमो)')}
            </Button>
            <p className="text-sm text-ink-2">{t('This demo has no PayPal keys, so PayPal is simulated.', 'इस डेमो में PayPal की चाबियां नहीं हैं, इसलिए PayPal नकली है।')}</p>
          </>
        )}
      </Card>

      {error && <Notice>{error}</Notice>}
      <Button variant="secondary" onClick={onCancel}>
        {t('Cancel', 'रद्द करें')}
      </Button>
    </div>
  );
}
