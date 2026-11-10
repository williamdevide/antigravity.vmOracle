import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Configuracao Vite com proxy para o backend FastAPI durante desenvolvimento local
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});

