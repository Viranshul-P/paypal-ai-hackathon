import { money, timeAgo } from '../../lib/format';
import type { AppEvent, Transfer } from '../../lib/types';
import { Card } from '../ui/Card';
import { StatusTag } from '../ui/StatusTag';

export function RecentPayments({ items }: { items: Transfer[] }) {
  return (
    <Card>
      <h2 className="text-2xl font-extrabold">Recent payments</h2>
      {items.length === 0 ? (
        <p className="mt-2 text-ink-2">Nothing yet. Payments appear here once they finish.</p>
      ) : (
        <ul className="mt-3 list-none divide-y divide-line p-0">
          {items.map((t) => (
            <li key={t.id} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="truncate font-semibold">{t.payee.name}</p>
                <p className="tabular text-sm text-ink-2">
                  {money(t.amount, t.currency)}, {timeAgo(t.created_at)}
                </p>
              </div>
              <StatusTag transfer={t} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function eventLabels(payer: string): Record<string, string> {
  return {
    assessed: 'Checked for warning signs',
    answered: `${payer} answered the questions`,
    'paypal.order_created': 'PayPal order created',
    'paypal.authorized': 'PayPal is holding the money',
    'paypal.captured': 'PayPal captured the payment',
    'paypal.payout_sent': 'PayPal paid the recipient',
    'paypal.voided': 'PayPal hold cancelled, nothing charged',
    'paypal.error': 'PayPal error',
    'paypal.authorization_denied': 'PayPal denied the hold',
    'held.cooling_off': 'Paused for the cooling-off period',
    'held.for_family': 'Held for your decision',
    'family.notified': 'Added to this page',
    'family.approved': 'You approved',
    'family.declined': 'You declined',
    cancelled: 'Cancelled',
  };
}

export function ActivityFeed({ events, payer }: { events: AppEvent[]; payer: string }) {
  const labels = eventLabels(payer);
  return (
    <Card>
      <h2 className="text-2xl font-extrabold">Activity</h2>
      <p className="text-ink-2">Every step, including each PayPal hold, capture, void and payout.</p>
      {events.length === 0 ? (
        <p className="mt-2 text-ink-2">No activity yet.</p>
      ) : (
        <ul className="mt-3 max-h-96 list-none divide-y divide-line overflow-y-auto p-0">
          {events.map((e) => (
            <li key={e.id} className="flex justify-between gap-3 py-2">
              <span className="font-semibold">{labels[e.kind] ?? e.kind.replace('webhook.', 'PayPal event: ')}</span>
              <span className="tabular shrink-0 text-sm text-ink-2">{timeAgo(e.at)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
