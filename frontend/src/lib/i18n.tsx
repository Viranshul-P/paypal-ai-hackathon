import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export type Lang = 'en' | 'hi';
const KEY = 'pauseline-lang';

function storedLang(): Lang {
  try {
    return localStorage.getItem(KEY) === 'hi' ? 'hi' : 'en';
  } catch {
    return 'en';
  }
}

interface I18n {
  lang: Lang;
  toggle: () => void;
  t: (en: string, hi: string) => string;
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(storedLang);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(KEY, lang);
    } catch {
      /* not remembered */
    }
  }, [lang]);

  const toggle = useCallback(() => setLang((l) => (l === 'hi' ? 'en' : 'hi')), []);
  const t = useCallback((en: string, hi: string) => (lang === 'hi' ? hi : en), [lang]);
  const value = useMemo(() => ({ lang, toggle, t }), [lang, toggle, t]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error('useI18n needs I18nProvider');
  return value;
}
