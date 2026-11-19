import { expect, test } from '@playwright/test';

const id = '12345678-1234-1234-1234-123456789abc';
const status = { available: true, busy: false, mode: 'experimental_buffered_video', quality_validated: false, confidence_calibrated: false };

// These fixtures test browser behaviour, not model accuracy. Real inference is
// checked independently against the local service and held-out recordings.
test.beforeEach(async ({ page }) => {
  await page.route('**/research/status', route => route.fulfill({ json: status }));
});

test('opens Interpreter without dataset labels and keeps Studio separate', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign. Be understood.' })).toBeVisible();
  await expect(page.getByLabel('Signer code', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('combobox')).toHaveCount(0);
  await expect(page.getByText('Experimental model connected')).toBeVisible();
  const stage = await page.locator('.camera-stage:visible').boundingBox();
  const enable = await page.getByRole('button', { name: 'Enable camera', exact: true }).boundingBox();
  expect(enable!.y + enable!.height).toBeLessThanOrEqual(stage!.y + stage!.height);
  await page.screenshot({ path: testInfo.outputPath('interpreter-desktop.png'), fullPage: true });
  await page.getByRole('button', { name: 'Enable camera', exact: true }).click();
  await expect(page.getByText('Camera on', { exact: true })).toBeVisible();
  await expect.poll(() => page.getByLabel('Interpreter camera preview').evaluate(video => (video as HTMLVideoElement).videoWidth)).toBeGreaterThan(0);
  expect(await page.getByLabel('Interpreter camera preview').evaluate(video => getComputedStyle(video).transform)).toContain('-1');
  await page.getByRole('button', { name: 'Contributor Studio', exact: true }).click();
  await expect(page.getByLabel('Signer code', { exact: true })).toBeVisible();
  expect(await page.getByLabel('Interpreter camera preview').evaluate(video => {
    const stream = (video as HTMLVideoElement).srcObject as MediaStream | null;
    return !stream || stream.getTracks().every(track => track.readyState === 'ended');
  })).toBe(true);
  await page.getByRole('button', { name: 'Interpreter', exact: true }).click();
  await expect(page.getByRole('combobox')).not.toBeVisible();
});

test('sends actual recorded video only on request and displays an unverified suggestion', async ({ page }) => {
  const uploads: Buffer[] = [];
  await page.route('**/research/jobs', async route => {
    expect(route.request().method()).toBe('POST');
    expect(route.request().headers()['content-type']).toContain('video/webm');
    expect(route.request().headers()['x-neosignis-request']).toBe('1');
    uploads.push(route.request().postDataBuffer()!);
    await route.fulfill({ status: 202, json: { id, state: 'processing' } });
  });
  await page.route(`**/research/jobs/${id}`, route => route.fulfill({ json: {
    id, state: 'complete', phase: 'translating', result: {
      disposition: 'needs_review', reason: 'unvalidated_model', candidate_text: 'Hello.',
      translated_text: null, confidence: null, quality_validated: false, elapsed_s: 2, segments: [],
    },
  } }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Enable camera', exact: true }).click();
  await page.getByRole('button', { name: 'Record a message', exact: true }).click();
  await expect.poll(async () => parseFloat(await page.locator('.recording-clock:visible').innerText())).toBeGreaterThanOrEqual(1);
  await page.getByRole('button', { name: 'Finish message', exact: true }).click();
  await expect(page.getByLabel('Message recording')).toBeVisible();
  expect(uploads).toHaveLength(0);
  await page.getByRole('button', { name: 'Interpret message', exact: true }).click();
  await expect(page.getByText('Unverified suggestion', { exact: true })).toBeVisible();
  await expect(page.getByText('Hello.', { exact: true })).toBeVisible();
  expect(uploads).toHaveLength(1);
  expect(uploads[0].length).toBeGreaterThan(1000);
  // EBML header: a real browser WebM, rather than JSON containing an answer.
  expect(uploads[0].subarray(0, 4).toString('hex')).toBe('1a45dfa3');
});

test('fits mobile browsers and discloses missing signed replies', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign. Be understood.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByLabel('Type a reply', { exact: true }).fill('Please repeat that.');
  await page.getByRole('button', { name: 'Show my reply', exact: true }).click();
  await expect(page.locator('.reply-text')).toHaveText('Please repeat that.');
  await expect(page.getByText(/Signed playback is not available yet/)).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('interpreter-mobile.png'), fullPage: true });
});
