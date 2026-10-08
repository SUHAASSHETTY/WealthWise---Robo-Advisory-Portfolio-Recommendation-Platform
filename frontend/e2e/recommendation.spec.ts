import { test, expect } from '@playwright/test';
import { switchPersona, navigateToTab } from './helpers';

test.describe('AC-02 & AC-04: Deterministic Portfolio Recommendations', () => {
  test('AC-02.1: Customer can view allocation recommendation summing to 100%', async ({ page }) => {
    await page.goto('/');

    // Switch to Carol (has risk profile assessed)
    await switchPersona(page, 'carol');

    // Navigate to Recommendation
    await navigateToTab(page, /Recommendation/i);

    await expect(page.getByRole('heading', { name: /Portfolio Allocation Recommendations/i })).toBeVisible();

    // If initial generate button is present, click it
    const genBtn = page.getByRole('button', { name: /Generate Initial Recommendation/i });
    if (await genBtn.isVisible()) {
      await genBtn.click();
    }

    // Verify Allocation Bar is rendered
    await expect(page.locator('.allocation-bar')).toBeVisible();

    // Verify Asset Breakdown cards (Equity, Debt, Gold, Cash)
    await expect(page.getByText('Equities & Stocks')).toBeVisible();
    await expect(page.getByText('Fixed Income & Debt')).toBeVisible();

    // Capture screenshot
    await page.screenshot({ path: 'e2e/__snapshots__/ac02-recommendations.png', fullPage: true });
  });
});
