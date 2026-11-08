import clsx from 'clsx';
import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

import { useConfig } from '../../lib/config';
import { Brand } from '../Brand';

const LINKS = [
  { to: '/send', label: 'Send money' },
  { to: '/family', label: 'Family view' },
  { to: '/setup', label: 'Setup' },
];

export function FamilyShell({ children }: { children: ReactNode }) {
  const config = useConfig();
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="flex flex-wrap items-center gap-x-8 gap-y-1 bg-card px-5 py-3 lg:px-10">
        <Brand />
        <nav aria-label="Main" className="flex gap-1">
          {LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx('rounded-full px-3 py-1.5 font-semibold whitespace-nowrap no-underline', isActive ? 'bg-action-soft text-action' : 'text-ink-2 hover:bg-tint')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 lg:px-10">{children}</main>
      <footer className="px-5 pb-6 text-center text-sm text-ink-2">
        PayPal {config.paypal_live ? 'sandbox' : 'demo mode'}. AI: {config.ai_mode}.
      </footer>
    </div>
  );
}
