import clsx from 'clsx';
import { Home, Send, Users } from 'lucide-react';
import { LayoutGroup, motion } from 'motion/react';
import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

import { useConfig } from '../lib/config';
import { useI18n } from '../lib/i18n';
import { Brand } from './Brand';

const CALM_GROUND = '#ffefe2';
const HELD_GROUND = '#ffd68c';

function LanguageToggle() {
  const { lang, toggle } = useI18n();
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Change language"
      className="min-h-11 rounded-full bg-card px-4 font-semibold text-action hover:bg-tint"
    >
      {lang === 'hi' ? 'English' : 'हिन्दी'}
    </button>
  );
}

// Adapted from Watermelon UI's Continuous Tabs: a pill that slides to the active tab.
function TabBar() {
  const { t } = useI18n();
  const tabs = [
    { to: '/', label: t('Home', 'होम'), icon: Home },
    { to: '/send', label: t('Pay', 'भेजें'), icon: Send },
    { to: '/family', label: t('Family', 'परिवार'), icon: Users },
  ];
  return (
    <LayoutGroup>
      <nav aria-label="Main" className="flex shrink-0 gap-1 rounded-t-card bg-card px-3 pt-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))]">
        {tabs.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end className="relative flex-1 rounded-full no-underline">
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.span
                    layoutId="tab-pill"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                    className="absolute inset-0 rounded-full bg-action-soft"
                  />
                )}
                <span className={clsx('relative flex min-h-14 flex-col items-center justify-center text-[0.85rem] font-semibold', isActive ? 'text-action' : 'text-ink-2')}>
                  <Icon className="size-5" aria-hidden />
                  {label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </LayoutGroup>
  );
}

interface PayerShellProps {
  held?: boolean; // the one full-screen colour change in the app
  rail: ReactNode;
  children: ReactNode;
}

// The payer side is a phone on every screen size. On a laptop, the rail explains what is happening.
export function PayerShell({ held = false, rail, children }: PayerShellProps) {
  const config = useConfig();
  return (
    <div className="lg:flex lg:min-h-dvh lg:items-center lg:justify-center lg:gap-20 lg:bg-backdrop lg:p-6">
      <aside className="hidden w-[30rem] lg:block">{rail}</aside>
      <motion.div
        animate={{ backgroundColor: held ? HELD_GROUND : CALM_GROUND }}
        initial={false}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        className="flex h-dvh w-full flex-col overflow-hidden lg:h-[min(52rem,calc(100dvh-3rem))] lg:w-[24.5rem] lg:shrink-0 lg:rounded-[2.75rem] lg:shadow-device"
      >
        <header className="flex shrink-0 items-center justify-between px-5 pt-[max(1.1rem,env(safe-area-inset-top))] pb-2">
          <Brand />
          <LanguageToggle />
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto px-4 pt-2 pb-5">{children}</main>
        <TabBar />
        <p className="sr-only">PayPal {config.paypal_live ? 'sandbox' : 'demo mode'}. AI: {config.ai_mode}.</p>
      </motion.div>
    </div>
  );
}
