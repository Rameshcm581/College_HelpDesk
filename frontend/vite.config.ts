import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8005',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 5175,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8005',
        changeOrigin: true,
      },
    },
  },
});
