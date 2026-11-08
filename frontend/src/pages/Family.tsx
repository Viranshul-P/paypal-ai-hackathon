import { Bell } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { PinGate } from '../components/PinGate';
import { FamilyShell } from '../components/family/FamilyShell';
import { ActivityFeed, RecentPayments } from '../components/family/History';
import { HoldCard } from '../components/family/HoldCard';
import { Card } from '../components/ui/Card';
import { ApiError, api, setFamilyPin } from '../lib/api';
import { useConfig } from '../lib/config';
import { money } from '../lib/format';
import type { FamilyOverview, Transfer } from '../lib/types';

function useAlerts(payer: string) {
  const supported = 'Notification' in window;
  const [permission, setPermission] = useState(supported ? Notification.permission : 'denied');
  const notify = useCallback(
    (t: Transfer) => {
      if (supported && Notification.permission === 'granted') {
        new Notification(`${payer}'s payment needs you`, { body: `${money(t.amount, t.currency)} to ${t.payee.name}` });
      }
    },
    [payer, supported],
  );
  const request = async () => setPermission(await Notification.requestPermission());
  return { supported, permission, notify, request };
}

function Dashboard() {
  const config = useConfig();
  const [data, setData] = useState<FamilyOverview | null>(null);
  const seen = useRef<Set<string> | null>(null); // null until first load, so old holds raise no alert
  const { supported, permission, notify, request } = useAlerts(config.payer_name);

  const refresh = useCallback(async () => {
    try {
      const next = await api<FamilyOverview>('/api/family/overview');
      setData(next);
      const ids = new Set(next.pending.map((t) => t.id));
      if (seen.current) {
        const fresh = next.pending.filter((t) => !seen.current!.has(t.id));
        if (fresh.length) notify(fresh[0]);
      }
      seen.current = ids;
      document.title = next.pending.length ? `(${next.pending.length}) Family view` : 'Family view';
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setFamilyPin('');
        window.location.reload();
      }
    }
  }, [notify]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => {
      clearInterval(timer);
      document.title = 'Pauseline';
    };
  }, [refresh]);

  async function decide(id: string, approve: boolean, note: string) {
    await api(`/api/transfers/${id}/family`, { method: 'POST', body: { approve, note } });
    await refresh();
  }

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[2.75rem] font-extrabold">{config.contact_name}'s view</h1>
          <p className="text-lg text-ink-2">You are {config.payer_name}'s trusted contact. Payments that look like a scam wait here for you.</p>
        </div>
        {supported && permission !== 'granted' && (
          <button
            type="button"
            disabled={permission === 'denied'}
            onClick={request}
            className="flex min-h-12 items-center gap-2 rounded-full bg-action-soft px-5 font-semibold text-action disabled:opacity-60"
          >
            <Bell className="size-5" aria-hidden />
            {permission === 'denied' ? 'Alerts are blocked in this browser' : 'Alert me in this browser'}
          </button>
        )}
      </div>

      <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <section aria-labelledby="pending-h" className="space-y-4">
          <h2 id="pending-h" className="text-2xl font-extrabold">
            Needs your decision
          </h2>
          {data === null && <p className="text-ink-2">Loading payments.</p>}
          {data?.pending.length === 0 && (
            <Card className="p-7">
              <p className="text-xl font-semibold">Nothing is waiting.</p>
              <p className="text-ink-2">Keep this page open and a paused payment will appear within seconds.</p>
            </Card>
          )}
          {data?.pending.map((t) => <HoldCard key={t.id} transfer={t} onDecide={decide} />)}
        </section>
        <div className="space-y-5">
          <RecentPayments items={data?.recent ?? []} />
          <ActivityFeed events={data?.events ?? []} payer={config.payer_name} />
        </div>
      </div>
    </>
  );
}

export default function Family() {
  return (
    <FamilyShell>
      <PinGate>
        <Dashboard />
      </PinGate>
    </FamilyShell>
  );
}
