import { test, expect } from '@playwright/test'

test('desktop registers, scoped review, guarded forms and export', async ({ page }) => {
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Governance overview' })).toBeVisible()
  await expect(page.locator('.loading-state')).toHaveCount(0)
  await expect(page.getByText('Connected to governance API')).toBeVisible()
  await expect(page.locator('.recharts-bar-rectangle').first()).toBeVisible()
  await page.screenshot({ path: 'test-results/overview-desktop.png', fullPage: true, animations: 'disabled' })
  for (const title of ['Allowlist & Requests', 'Inventory Reviews', 'Skills Catalog', 'Sharing & Visibility', 'Data Sources', 'Rollout Gates', 'Configuration Baselines', 'Change Control', 'Evidence Library', 'Retention Positions', 'Audit Explorer', 'Acceptable Use Incidents']) {
    await page.getByRole('button', { name: title, exact: false }).first().click()
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await expect(page.locator('.table-shell')).toBeVisible()
  }
  await page.getByRole('button', { name: 'Allowlist & Requests' }).click()
  await page.getByRole('tab', { name: 'Claude', exact: true }).click()
  await expect(page.locator('tbody tr')).not.toHaveCount(0)
  await expect(page.locator('tbody .platform-name:not(.claude)')).toHaveCount(0)
  const requestName = `Browser Test Agent ${Date.now()}`
  await page.getByRole('button', { name: 'New request', exact: true }).click()
  await page.getByLabel('Name', { exact: true }).fill(requestName)
  await page.getByLabel('Owner', { exact: true }).fill('Synthetic Browser Reviewer')
  await page.getByLabel('External Id').fill(`browser-test-${Date.now()}`)
  await page.getByLabel('Justification').fill('Synthetic browser workflow validation')
  await page.getByLabel('Kind', { exact: true }).selectOption('agent')
  await page.getByRole('button', { name: 'Save record' }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await page.getByLabel('Search records').fill(requestName)
  await page.getByRole('button', { name: requestName, exact: true }).click()
  await expect(page.getByRole('dialog').getByText('Disabled', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Close', exact: true }).last().click()
  await page.getByRole('button', { name: 'Audit package', exact: true }).click()
  const downloaded = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export package', exact: true }).click()
  expect((await downloaded).suggestedFilename()).toMatch(/aigovern-claude-.*\.zip/)
  expect(errors).toEqual([])
})

test('mobile navigation and layout remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.locator('.loading-state')).toHaveCount(0)
  await expect(page.getByText('Connected to governance API')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/overview-mobile.png', fullPage: true, animations: 'disabled' })
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('button', { name: 'Inventory Reviews', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Inventory Reviews', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Import', exact: true })).toBeVisible()
  await expect(page.locator('.nav-scrim')).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/inventory-mobile.png', fullPage: true, animations: 'disabled' })
})

test('credential dialog normalizes Bearer prefixes and keeps rejected keys editable', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.loading-state')).toHaveCount(0)
  let authorization = ''
  await page.route('**/api/session', async (route) => {
    const header = route.request().headers().authorization || ''
    if (header) authorization = header
    if (authorization === 'Bearer invalid-test-key') {
      await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Valid bearer credential required' }) })
      return
    }
    await route.continue()
  })

  await page.getByRole('button', { name: 'Credentials' }).click()
  const dialog = page.getByRole('dialog')
  const credential = page.getByLabel('Railway API key')
  await credential.fill('Bearer invalid-test-key')
  await page.getByRole('button', { name: 'Connect', exact: true }).click()
  await expect(dialog.getByText('Valid bearer credential required')).toBeVisible()
  await expect(dialog).toBeVisible()
  expect(authorization).toBe('Bearer invalid-test-key')

  await credential.fill('Bearer valid-test-key')
  await page.getByRole('button', { name: 'Connect', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('aigovern-token'))).toBe('valid-test-key')
  expect(authorization).toBe('Bearer valid-test-key')
})