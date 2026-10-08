import { test, expect } from '@playwright/test';
import { switchPersona, navigateToTab } from './helpers';

test.describe('AC-05: Holdings Valuation & Allocation Drift', () => {
  test('AC-05.1: Customer can view holdings valuation and drift calculation per asset class', async ({
    page,
  }) => {
    await page.goto('/');

    // Switch to Alice (has active portfolio and holdings)
    await switchPersona(page, 'alice');

    // Navigate to Holdings
    await navigateToTab(page, /Holdings & Drift/i);

    await expect(page.getByRole('heading', { name: /Portfolio Holdings & Allocation Drift/i })).toBeVisible();

    // Verify KPI Cards
    await expect(page.getByText(/Total Portfolio Valuation/i)).toBeVisible();
    await expect(page.getByText(/Portfolio Balance Status/i)).toBeVisible();

    // Verify asset class is visible on either desktop table or mobile card
    await expect(page.getByText('EQUITY').first()).toBeVisible();

    // Capture screenshot
    await page.screenshot({ path: 'e2e/__snapshots__/ac05-holdings-drift.png', fullPage: true });
  });
});
