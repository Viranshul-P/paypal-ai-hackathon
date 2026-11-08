import clsx from 'clsx';
import { CircleAlert } from 'lucide-react';
import type { ReactNode } from 'react';

// Adapted from Watermelon UI's Alert 25: a soft, borderless callout.
export function Notice({ tone = 'stop', children }: { tone?: 'stop' | 'held'; children: ReactNode }) {
  return (
    <div
      role="alert"
      className={clsx(
        'flex items-start gap-3 rounded-2xl px-4 py-3 font-semibold',
        tone === 'stop' ? 'bg-stop-soft text-stop' : 'bg-held-soft text-held',
      )}
    >
      <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}
