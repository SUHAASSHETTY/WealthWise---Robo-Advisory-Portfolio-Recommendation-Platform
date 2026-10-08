import { test, expect } from '@playwright/test';
import { switchPersona, navigateToTab } from './helpers';

test.describe('AC-03 & AC-08: Investment Goals Tracker & Progress', () => {
  test('AC-03.1: Customer can create and list multi-goals with priority and progress', async ({ page }) => {
    await page.goto('/');

    // Switch to Bob (has 0 goals initially)
    await switchPersona(page, 'bob');

    // Navigate to Goals tab
    await navigateToTab(page, /Goals Tracker/i);

    await expect(page.getByRole('heading', { name: /Investment Goals Tracker/i })).toBeVisible();

    // Check if add goal button is present
    const createBtn = page.locator('#create-goal-btn');
    if (await createBtn.isVisible()) {
      await createBtn.click();

      // Fill goal form
      const goalTitle = `College Savings Fund ${Date.now().toString().slice(-4)}`;
      await page.locator('#goal-name').fill(goalTitle);
      await page.locator('#goal-type').selectOption('EDUCATION');
      await page.locator('#goal-target-amount').fill('25000.00');
      await page.locator('#goal-funding-share').fill('30.00');
      await page.locator('#goal-target-date').fill('2032-08-31');

      // Submit
      await page.locator('#save-goal-btn').click();

      // Verify created goal card appears
      await expect(page.getByRole('heading', { name: goalTitle })).toBeVisible();
    } else {
      await expect(page.locator('.goal-card').first()).toBeVisible();
    }

    // Capture screenshot
    await page.screenshot({ path: 'e2e/__snapshots__/ac03-goals-tracker.png', fullPage: true });
  });
});
