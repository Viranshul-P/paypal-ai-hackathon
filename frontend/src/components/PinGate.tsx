import { useEffect, useState, type ReactNode } from 'react';

import { ApiError, api, getFamilyPin, setFamilyPin } from '../lib/api';
import { useConfig } from '../lib/config';
import { Card } from './ui/Card';
import { Notice } from './ui/Notice';
import { PinInput } from './ui/PinInput';

async function pinIsRight() {
  try {
    await api('/api/family/overview');
    return true;
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return false;
    throw e;
  }
}

export function PinGate({ children }: { children: ReactNode }) {
  const config = useConfig();
  const [state, setState] = useState<'checking' | 'locked' | 'open'>(getFamilyPin() ? 'checking' : 'locked');
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (state !== 'checking') return;
    pinIsRight()
      .then((ok) => {
        if (!ok) setFamilyPin('');
        setState(ok ? 'open' : 'locked');
      })
      .catch(() => setState('locked'));
  }, [state]);

  async function submit(pin: string) {
    setBusy(true);
    setError('');
    setFamilyPin(pin);
    try {
      if (await pinIsRight()) {
        setState('open');
        return;
      }
      setError('That PIN is not right. Check it and try again.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not check the PIN. Try again.');
    }
    setFamilyPin('');
    setValue('');
    setBusy(false);
  }

  if (state === 'open') return <>{children}</>;
  if (state === 'checking') return null;

  return (
    <Card className="mx-auto mt-10 max-w-md space-y-5 p-7 text-center">
      <div>
        <h1 className="text-3xl font-extrabold">Enter the family PIN</h1>
        <p className="mt-2 text-ink-2">
          Only {config.contact_name} should open this page. If someone on the phone asks {config.payer_name} to open it, that is a scam.
        </p>
      </div>
      <PinInput value={value} onChange={setValue} onComplete={submit} disabled={busy} />
      {error && <Notice>{error}</Notice>}
      {config.demo_pin && <p className="text-sm text-ink-2">This demo uses the PIN {config.demo_pin}.</p>}
    </Card>
  );
}
