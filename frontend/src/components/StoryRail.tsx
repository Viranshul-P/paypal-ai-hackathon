import clsx from 'clsx';
import { Check } from 'lucide-react';
import { Link } from 'react-router-dom';

import { useConfig } from '../lib/config';

const STEPS = [
  { title: 'The payer says what it is for', body: 'By voice or text, in English, Hindi or Hinglish.' },
  { title: 'Pauseline checks for scam pressure', body: 'Their words and the payment context, then up to two yes or no questions.' },
  { title: 'PayPal holds the money', body: 'An authorisation reserves the funds. Nothing is taken yet.' },
  { title: 'A rule or the family decides', body: 'Normal payments go at once. Risky ones wait, and a decline voids the hold.' },
];

export function StoryRail({ current, done = false }: { current: number; done?: boolean }) {
  const config = useConfig();
  return (
    <div>
      <h1 className="text-5xl font-extrabold">What is happening</h1>
      <ol className="mt-8 space-y-5">
        {STEPS.map((step, i) => {
          const finished = done || i < current;
          const active = !done && i === current;
          return (
            <li key={step.title} className="flex gap-4">
              <span
                className={clsx(
                  'flex size-10 shrink-0 items-center justify-center rounded-full text-lg font-extrabold transition-colors duration-200',
                  finished && 'bg-sent-soft text-sent',
                  active && 'bg-ink text-white',
                  !finished && !active && 'bg-card text-ink-2',
                )}
              >
                {finished ? <Check className="size-5" aria-label="Done" /> : i + 1}
              </span>
              <div>
                <p className={clsx('text-xl font-semibold', !active && !finished && 'text-ink-2')}>{step.title}</p>
                <p className="text-ink-2">{step.body}</p>
              </div>
            </li>
          );
        })}
      </ol>
      <p className="mt-8 text-ink-2">
        Held payments appear in{' '}
        <Link to="/family" target="_blank" className="font-semibold text-action">
          {config.contact_name}'s Family view
        </Link>
        .
      </p>
      <p className="mt-2 text-sm text-ink-2">
        PayPal {config.paypal_live ? 'sandbox' : 'demo mode'}. AI: {config.ai_mode}.
      </p>
    </div>
  );
}
