import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/echarts')) return 'echarts'
          if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router')) return 'vue-vendor'
        }
      }
    }
  },
  server: {
    host: '127.0.0.1',
    port: 3001,
    allowedHosts: ['data.kaiamu.top', 'kaiamu.top', 'all'],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true
      }
    }
  }
})
