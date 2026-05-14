import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/ask': 'http://127.0.0.1:8080',
      '/documents': 'http://127.0.0.1:8080',
      '/retrieve': 'http://127.0.0.1:8080',
      '/improvement-cases': 'http://127.0.0.1:8080',
      '/introspection': 'http://127.0.0.1:8080',
      '/prompts': 'http://127.0.0.1:8080',
      '/experiments': 'http://127.0.0.1:8080',
      '/eval': 'http://127.0.0.1:8080',
      '/health': 'http://127.0.0.1:8080',
      '/observability': 'http://127.0.0.1:8080',
    },
  },
});
