import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { MotionConfig } from 'motion/react';

import '@fontsource/baloo-2/latin-400.css';
import '@fontsource/baloo-2/latin-600.css';
import '@fontsource/baloo-2/latin-800.css';
import '@fontsource/baloo-2/devanagari-400.css';
import '@fontsource/baloo-2/devanagari-600.css';
import '@fontsource/baloo-2/devanagari-800.css';
import './index.css';

import App from './App';
import { ConfigProvider } from './lib/config';
import { I18nProvider } from './lib/i18n';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <I18nProvider>
          <ConfigProvider>
            <App />
          </ConfigProvider>
        </I18nProvider>
      </BrowserRouter>
    </MotionConfig>
  </StrictMode>,
);
