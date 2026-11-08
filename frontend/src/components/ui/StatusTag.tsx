import clsx from 'clsx';

import { useI18n } from '../../lib/i18n';
import type { Transfer } from '../../lib/types';

// The one vocabulary for payment state, used everywhere a payment is shown.
const LABELS = {
  draft: ['Being checked', 'जांच जारी'],
  awaiting_payer: ['Waiting for PayPal', 'PayPal का इंतज़ार'],
  held: ['On hold', 'रोका गया'],
  released: ['Sent', 'भेजा गया'],
  cancelled: ['Cancelled', 'रद्द'],
  failed: ['Failed', 'असफल'],
} as const;

const TONES = {
  draft: 'bg-tint text-ink-2',
  awaiting_payer: 'bg-tint text-ink-2',
  held: 'bg-held-soft text-held',
  released: 'bg-sent-soft text-sent',
  cancelled: 'bg-stop-soft text-stop',
  failed: 'bg-stop-soft text-stop',
} as const;

export function StatusTag({ transfer }: { transfer: Pick<Transfer, 'status' | 'delivery_failed'> }) {
  const { t } = useI18n();
  const status = transfer.delivery_failed ? 'failed' : transfer.status;
  const label = transfer.delivery_failed ? t('Not delivered', 'नहीं पहुंचा') : t(LABELS[status][0], LABELS[status][1]);
  return (
    <span className={clsx('inline-block rounded-full px-3 py-0.5 text-sm font-semibold whitespace-nowrap', TONES[status])}>
      {label}
    </span>
  );
}
