import { test, expect } from '@playwright/test';

test('increments count when button is clicked', async ({ page }) => {
  await page.goto('http://localhost:5173/');

  const button = page.getByRole('button', { name: 'Increment' });
  const counter = page.getByText(/Count:/);

  await expect(counter).toHaveText('Count: 0');

  await button.click();

  await expect(counter).toHaveText('Count: 1');
});
