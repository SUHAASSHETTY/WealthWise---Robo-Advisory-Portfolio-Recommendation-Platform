import { type Page, expect } from '@playwright/test';

export async function switchPersona(page: Page, personaId: 'alice' | 'bob' | 'carol' | 'dan' | 'erin') {
  await page.locator('#role-switcher-trigger').click();
  const option = page.locator(`#persona-option-${personaId}`);
  await expect(option).toBeVisible();
  await option.click();
  await page.waitForTimeout(300);
}

export async function navigateToTab(page: Page, labelRegex: RegExp) {
  const menuToggle = page.locator('#menu-toggle-btn');
  if (await menuToggle.isVisible()) {
    const isSidebarVisible = await page.locator('.sidebar--open').isVisible();
    if (!isSidebarVisible) {
      await menuToggle.click();
      await page.waitForTimeout(200);
    }
  }
  const linkBtn = page.getByRole('button', { name: labelRegex });
  await expect(linkBtn).toBeVisible();
  await linkBtn.click();
  await page.waitForTimeout(300);
}
