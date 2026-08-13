/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import fs from 'fs'

function ngrokPlugin() {
  let ngrokProc: ChildProcess | null = null

  return {
    name: 'vite-plugin-ngrok',
    configureServer(server: any) {
      server.httpServer?.once('listening', async () => {
        const rootNgrokPath = path.resolve(import.meta.dirname, '../ngrok.exe')
        const ngrokCmd = fs.existsSync(rootNgrokPath) ? rootNgrokPath : 'ngrok'

        try {
          // Check if ngrok is already running
          const checkRes = await fetch('http://127.0.0.1:4040/api/tunnels').catch(() => null)
          if (checkRes && checkRes.ok) {
            const data = (await checkRes.json()) as any
            const existingUrl = data.tunnels?.[0]?.public_url
            if (existingUrl) {
              console.log(`\n  ➜  \x1b[36m\x1b[1mngrok\x1b[0m:   \x1b[36m${existingUrl}\x1b[0m\n`)
              return
            }
          }

          // Start ngrok automatically
          ngrokProc = spawn(ngrokCmd, ['http', '3233'], {
            stdio: 'ignore',
            detached: false,
          })

          for (let i = 0; i < 10; i++) {
            await new Promise((r) => setTimeout(r, 500))
            const res = await fetch('http://127.0.0.1:4040/api/tunnels').catch(() => null)
            if (res && res.ok) {
              const data = (await res.json()) as any
              const url = data.tunnels?.[0]?.public_url
              if (url) {
                console.log(`\n  ➜  \x1b[36m\x1b[1mngrok\x1b[0m:   \x1b[36m${url}\x1b[0m\n`)
                break
              }
            }
          }
        } catch (e) {
          // Ignore if ngrok is missing
        }
      })

      const cleanup = () => {
        if (ngrokProc) {
          ngrokProc.kill()
          ngrokProc = null
        }
      }

      process.on('exit', cleanup)
      process.on('SIGINT', cleanup)
      process.on('SIGTERM', cleanup)
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  server: {
    port: 3233,
    host: true,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:4500',
        changeOrigin: true,
      },
    },
  },
  plugins: [react(), ngrokPlugin()],
  test: {
    environment: 'jsdom',
  },
})

