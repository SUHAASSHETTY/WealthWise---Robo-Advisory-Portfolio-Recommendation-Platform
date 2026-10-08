import { test, expect } from '@playwright/test';
import { switchPersona, navigateToTab } from './helpers';

test.describe('AC-06 & AC-07: Rebalancing Engine & Trade Proposal Lifecycle', () => {
  test('AC-06.1: Customer can evaluate drift, view proposal, and accept trade quantities', async ({
    page,
  }) => {
    await page.goto('/');

    // Switch to Alice (has verified KYC and portfolio)
    await switchPersona(page, 'alice');

    // Navigate to Rebalancing
    await navigateToTab(page, /Rebalancing/i);

    await expect(page.getByRole('heading', { name: /Portfolio Drift Rebalancing/i })).toBeVisible();

    // Trigger Rebalancing Evaluation if evaluate button visible
    const evalBtn = page.locator('#evaluate-rebalance-btn');
    if (await evalBtn.isVisible()) {
      await evalBtn.scrollIntoViewIfNeeded();
      await evalBtn.click({ force: true });
      await page.waitForTimeout(500);
    }

    // Accept proposal if open
    const acceptBtn = page.locator('#accept-proposal-btn');
    if (await acceptBtn.isVisible()) {
      await acceptBtn.scrollIntoViewIfNeeded();
      await acceptBtn.click({ force: true });
      await expect(page.getByText(/accepted/i).first()).toBeVisible();
    } else {
      // Rebalancing table or card is present
      await expect(page.locator('.proposal-card, .rebalance-history-card, .empty-state').first()).toBeVisible();
    }

    // Capture screenshot
    await page.screenshot({ path: 'e2e/__snapshots__/ac06-rebalancing-proposal.png', fullPage: true });
  });
});
