import { defineConfig } from '@playwright/test'

const deploymentUrl = process.env.AIGOVERN_DEPLOYMENT_URL
const deploymentConfigured = Boolean(deploymentUrl && process.env.AIGOVERN_DEPLOYMENT_TOKEN)

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: deploymentConfigured ? deploymentUrl : 'http://127.0.0.1:5173', screenshot: 'only-on-failure', trace: deploymentConfigured ? 'off' : 'retain-on-failure' },
  webServer: deploymentConfigured ? undefined : [
    { command: process.platform === 'win32' ? '"../.venv/Scripts/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir ../backend' : 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir ../backend', url: 'http://127.0.0.1:8000/api/health', reuseExistingServer: !process.env.CI, env: { ENVIRONMENT: 'development', ADMIN_API_KEY: '', REVIEWER_API_KEY: '', VIEWER_API_KEY: '' } },
    { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
  ],
})