import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    // ✅ 就是加了这一行，解决拦截
    allowedHosts: ['data.kaiamu.top', 'kaiamu.top', 'all'],
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true
      }
    }
  }
})