import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// В режиме npm run dev запросы /api и /auth уходят на локальные сервисы
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8002',
      '/auth': 'http://localhost:8001',
    },
  },
})
