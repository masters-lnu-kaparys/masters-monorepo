import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          map: ['leaflet', 'react-leaflet'],
          ui: ['@mui/material', '@emotion/react', '@emotion/styled'],
          auth: ['@auth0/auth0-react'],
        },
      },
    },
  },
})
