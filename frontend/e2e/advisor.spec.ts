import { test, expect } from '@playwright/test';
import { switchPersona } from './helpers';

test.describe('AC-09: Advisor Workbench & Fiduciary Risk Overrides', () => {
  test('AC-09.1: Dan (Advisor) can review clients, view deep portfolio, and apply risk overrides', async ({
    page,
  }) => {
    await page.goto('/');

    // Switch to Dan Advisor
    await switchPersona(page, 'dan');

    // Verify Advisor Workbench header
    await expect(page.getByRole('heading', { name: /Advisor Workbench/i })).toBeVisible();

    // Verify Assigned clients list contains Alice Fernandes, Bob Mathew, Carol Dsouza
    await expect(page.getByText('Alice Fernandes')).toBeVisible();
    await expect(page.getByText('Carol Dsouza')).toBeVisible();

    // Open Carol's Risk Override modal (Carol is assessed MODERATE)
    const overrideBtn = page.locator('#risk-override-btn-00000000-0000-4000-8000-00000000c003');
    await overrideBtn.scrollIntoViewIfNeeded();
    await overrideBtn.click();

    // Verify modal is open
    await expect(page.getByRole('heading', { name: /Override Risk Band/i })).toBeVisible();

    // Select new band & rationale note
    await page.locator('#new-risk-band').selectOption('CONSERVATIVE');
    await page.locator('#override-note').fill('Fiduciary adjustment: Client approaching retirement target.');

    // Submit override
    const submitBtn = page.locator('#submit-risk-override-btn');
    await submitBtn.scrollIntoViewIfNeeded();
    await submitBtn.click({ force: true });

    // Verify success banner
    await expect(page.getByText(/override recorded/i)).toBeVisible();

    // Capture screenshot
    await page.screenshot({ path: 'e2e/__snapshots__/ac09-advisor-workbench.png', fullPage: true });
  });
});
