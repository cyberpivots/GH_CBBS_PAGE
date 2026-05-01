import { expect, test } from '@playwright/test';

test('home page renders public marketing surface', async ({ page }) => {
  await page.goto('/GH_CBBS_PAGE/');

  await expect(page.getByRole('heading', { name: /off-grid bulletin boards/i })).toBeVisible();
  await expect(page.getByRole('navigation', { name: /primary/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /explore systems/i })).toBeVisible();
});

test('system navigation works on mobile without horizontal overflow', async ({ page }) => {
  await page.goto('/GH_CBBS_PAGE/');
  await page.getByRole('link', { name: 'Systems', exact: true }).click();

  await expect(page.getByRole('heading', { name: 'CBBS system layers' })).toBeVisible();

  const overflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth - window.innerWidth;
  });

  expect(overflow).toBeLessThanOrEqual(1);
});

test('media gallery labels current and prototype assets', async ({ page }) => {
  await page.goto('/GH_CBBS_PAGE/media/');

  await expect(page.getByRole('heading', { name: /CBBS interface gallery/i })).toBeVisible();
  await expect(page.getByText('Current system', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Prototype display', { exact: true }).first()).toBeVisible();
});

test('workflow explorer switches scenarios', async ({ page }) => {
  await page.goto('/GH_CBBS_PAGE/workflows/');

  await page.getByRole('tab', { name: 'Flood EOC bring-up' }).click();
  await expect(page.getByRole('heading', { name: 'Flood EOC bring-up' })).toBeVisible();
  await expect(page.getByText(/example scenario, not a deployment report/i)).toBeVisible();
});
