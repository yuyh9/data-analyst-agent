import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 3000,
    proxy: {
      '/chat': 'http://localhost:8000',
      '/session': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
      '/tables': 'http://localhost:8000',
      '/charts': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})