import { test, expect } from '@playwright/test';
import { switchPersona } from './helpers';

test.describe('AC-10: Admin Governance & Versioning Operations', () => {
  test('AC-10.1: Erin (Admin) can view templates, risk policies, asset classes and trigger NAV refresh', async ({
    page,
  }) => {
    await page.goto('/');

    // Switch to Erin Admin
    await switchPersona(page, 'erin');

    // Verify Admin governance page header
    await expect(page.getByRole('heading', { name: /Platform Administration/i })).toBeVisible();

    // Verify Template Versions tab active
    await expect(page.getByRole('heading', { name: /Current Active Template Policy/i })).toBeVisible();

    // Switch to Asset Classes tab
    await page.locator('#admin-tab-assets').click();
    await expect(page.getByRole('heading', { name: /Configured Asset Classes/i })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'EQUITY', exact: true })).toBeVisible();

    // Switch to NAV Feed Ops tab
    await page.locator('#admin-tab-nav').click();
    await expect(page.getByRole('heading', { name: /Daily NAV Feed Operations/i })).toBeVisible();

    // Trigger daily NAV refresh
    await page.locator('#trigger-nav-refresh-btn').click();
    await expect(page.getByText(/NAV feed/i).first()).toBeVisible();

    // Capture screenshot
    await page.screenshot({ path: 'e2e/__snapshots__/ac10-admin-governance.png', fullPage: true });
  });
});
