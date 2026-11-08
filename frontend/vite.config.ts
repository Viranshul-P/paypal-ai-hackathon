import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// The build is committed to src/pauseline/web so the app still runs with Python alone.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { outDir: '../src/pauseline/web', emptyOutDir: true },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/webhooks': 'http://127.0.0.1:8000',
      '/favicon.ico': 'http://127.0.0.1:8000',
    },
  },
});
