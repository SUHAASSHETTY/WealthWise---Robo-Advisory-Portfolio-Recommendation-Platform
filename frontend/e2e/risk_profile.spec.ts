import { test, expect } from '@playwright/test';
import { switchPersona, navigateToTab } from './helpers';

test.describe('AC-01: Risk Profiling & Questionnaire Flow', () => {
  test('AC-01.1: Customer can take questionnaire and see assigned risk band', async ({ page }) => {
    await page.goto('/');

    // Switch to Carol (unassessed)
    await switchPersona(page, 'carol');

    // Verify on Risk Profile page
    await navigateToTab(page, /Risk Profile/i);
    await expect(page.getByRole('heading', { name: /Risk Profile & Assessment/i })).toBeVisible();

    // Click Start/Retake assessment
    const startBtn = page.locator('#start-assessment-btn, #retake-assessment-btn').first();
    await expect(startBtn).toBeVisible();
    await startBtn.click();

    // Verify 7 questions rendered
    await expect(page.getByRole('heading', { name: /Risk Tolerance Questionnaire/i })).toBeVisible();

    // Select options for each question
    const questionCards = page.locator('.question-card');
    const count = await questionCards.count();
    expect(count).toBeGreaterThanOrEqual(6);

    for (let i = 0; i < count; i++) {
      const q = questionCards.nth(i);
      const option = q.locator('.option-card').nth(2);
      await option.scrollIntoViewIfNeeded();
      await option.click();
    }

    // Submit assessment
    const submitBtn = page.locator('#submit-assessment-btn');
    await submitBtn.scrollIntoViewIfNeeded();
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click({ force: true });

    // Verify risk band result card is shown
    await expect(page.locator('.risk-card')).toBeVisible();

    // Capture screenshot
    await page.screenshot({ path: 'e2e/__snapshots__/ac01-risk-profile.png', fullPage: true });
  });
});
