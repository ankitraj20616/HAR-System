import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api/feedback': 'http://localhost:8002',
      '/api': 'http://localhost:8001',
      '/feedback-ws': { target: 'ws://localhost:8002', ws: true, rewrite: () => '/ws' },
      '/ws': { target: 'ws://localhost:8001', ws: true },
    },
  },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts' },
});
