import { defineConfig } from '@playwright/test'

const deploymentUrl = process.env.AIGOVERN_DEPLOYMENT_URL

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: deploymentUrl || 'http://127.0.0.1:5173', screenshot: 'only-on-failure', trace: deploymentUrl ? 'off' : 'retain-on-failure' },
  webServer: deploymentUrl ? undefined : [
    { command: process.platform === 'win32' ? '"../.venv/Scripts/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir ../backend' : 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir ../backend', url: 'http://127.0.0.1:8000/api/health', reuseExistingServer: !process.env.CI },
    { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
  ],
})