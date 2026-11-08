import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

import { api } from './api';
import type { AppConfig } from './types';

const ConfigContext = createContext<AppConfig | null>(null);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api<AppConfig>('/api/config').then(setConfig, () => setFailed(true));
  }, []);

  if (failed) {
    return (
      <p className="p-8 text-lg">
        Pauseline could not start. Check your connection, then reload this page.
      </p>
    );
  }
  if (!config) return null;
  return <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>;
}

export function useConfig() {
  const config = useContext(ConfigContext);
  if (!config) throw new Error('useConfig needs ConfigProvider');
  return config;
}
