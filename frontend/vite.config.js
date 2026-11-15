import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    // Solo para el modo desarrollo (`npm run dev`, puerto 5173).
    // El frontend llama a rutas relativas `/api/v1/...`; aquí las redirigimos
    // al backend FastAPI en el 8000. Gracias a esto el mismo código funciona
    // servido desde el build (`python -m uvicorn main:app`, todo en el 8000)
    // y desde el servidor de desarrollo de Vite.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
