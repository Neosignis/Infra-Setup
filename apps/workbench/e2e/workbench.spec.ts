import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import JSZip from 'jszip';

test('connects to the real API without claiming a recognition model', async ({ page, request }, testInfo) => {
  await page.goto('/');
  await expect(page.getByText('Connected', { exact: true })).toBeVisible();
  await expect(page.getByText('Not installed', { exact: true })).toBeVisible();
  const capabilities = await request.get('/engine/v1/capabilities');
  expect(capabilities.ok()).toBe(true);
  const body = await capabilities.json();
  expect(body.languages.every((item: { recognize: boolean }) => !item.recognize)).toBe(true);
  await expect(page.getByRole('button', { name: 'Start recording', exact: true })).toBeDisabled();
  await page.screenshot({ path: testInfo.outputPath('desktop.png'), fullPage: true });
});

test('records simulated camera video, reviews it and exports verifiable bytes', async ({ page }) => {
  const unexpectedWrites: string[] = [];
  page.on('request', request => {
    if (!['GET', 'HEAD'].includes(request.method())) unexpectedWrites.push(request.url());
  });
  await page.goto('/');
  await page.getByLabel('Signer code', { exact: true }).fill('test-signer');
  await page.getByLabel('Recording permission reference', { exact: true }).fill('test-permission');
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Enable camera', exact: true }).click();
  await expect(page.getByText('Camera on', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Start recording', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Finish recording', exact: true })).toBeVisible();
  // Exercise real MediaRecorder rather than a mocked recording fixture.
  await expect.poll(async () => parseFloat(await page.locator('.recording-clock').innerText())).toBeGreaterThanOrEqual(1);
  await page.getByRole('button', { name: 'Finish recording', exact: true }).click();
  await expect(page.locator('.clip-total')).toHaveText('01');
  await expect(page.getByRole('heading', { name: 'Review your session.' })).toBeVisible();
  await expect(page.getByText('Recording saved in this tab. Play it below, or')).toBeVisible();
  const playback = page.getByLabel('Recorded signing clip', { exact: true });
  await expect(playback).toBeVisible();
  await expect.poll(() => playback.evaluate(element => (element as HTMLVideoElement).readyState)).toBeGreaterThanOrEqual(1);
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download session ZIP', exact: true }).click();
  const archive = await downloaded;
  const localPath = await archive.path();
  expect(localPath).not.toBeNull();
  const zip = await JSZip.loadAsync(await readFile(localPath!));
  const manifest = JSON.parse(await zip.file('manifest.json')!.async('string'));
  expect(manifest.clips).toHaveLength(1);
  expect(manifest.training_authorized).toBe(false);
  expect(manifest.clips[0].signer_id).toBe('test-signer');
  expect(manifest.clips[0].split).toBe('unassigned');
  expect(manifest.clips[0].recording_mirrored).toBe(false);
  const recording = await zip.file(manifest.clips[0].file)!.async('nodebuffer');
  expect(recording.length).toBeGreaterThan(1000);
  expect(createHash('sha256').update(recording).digest('hex')).toBe(manifest.clips[0].sha256);
  expect(manifest.clips[0].duration_ms).toBeGreaterThan(500);
  expect(manifest.clips[0].duration_ms).toBeLessThanOrEqual(10_000);
  // Prove that browser exports satisfy the Python ingestion boundary too.
  const validation = JSON.parse(execFileSync('python3', ['../../scripts/data/validate_capture.py', localPath!], { encoding: 'utf8' }));
  expect(validation.status).toBe('capture_integrity_passed');
  expect(validation.training_ready).toBe(false);
  expect(unexpectedWrites).toEqual([]);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
  await page.getByRole('button', { name: 'Discard clip', exact: true }).click();
  await expect(page.getByText('Your first clip starts an exchange.')).toBeVisible();
  await page.getByRole('button', { name: /Camera capture/ }).click();
  await page.getByRole('button', { name: 'Turn camera off', exact: true }).click();
  await expect(page.getByText('Camera off', { exact: true })).toBeVisible();
});

test('handles a declined camera request and an offline API', async ({ page }) => {
  await page.route('**/engine/v1/capabilities', route => route.abort());
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Test declined permission', 'NotAllowedError'); };
  });
  await page.goto('/');
  await expect(page.getByText('Offline', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Enable camera', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Camera permission was declined');
  await expect(page.getByRole('button', { name: 'Start recording', exact: true })).toBeDisabled();
});

test('has no horizontal overflow on a narrow screen', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Capture a signing sample.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const stage = await page.locator('.camera-stage').boundingBox();
  const instruction = await page.getByRole('heading', { name: 'A little space for both hands.' }).boundingBox();
  expect(instruction!.x).toBeGreaterThanOrEqual(stage!.x);
  expect(instruction!.x + instruction!.width).toBeLessThanOrEqual(stage!.x + stage!.width);
  expect(stage!.x + stage!.width).toBeLessThanOrEqual(390);
  await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true });
});


test('camera preview explains missing setup and never silently starts recording', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Enable camera', exact: true }).click();
  const start = page.getByRole('button', { name: 'Start recording', exact: true });
  await expect(start).toBeEnabled();
  await expect(page.locator('#capture-status')).toContainText('Preview only');
  await start.click();
  await expect(page.getByRole('alert')).toContainText('Before recording: Enter a signer code');
  await expect(page.getByLabel('Signer code', { exact: true })).toBeFocused();
  await page.getByLabel('Signer code', { exact: true }).fill('test-signer');
  await start.click();
  await expect(page.getByLabel('Recording permission reference', { exact: true })).toBeFocused();
  await page.getByLabel('Recording permission reference', { exact: true }).fill('test-permission');
  await start.click();
  await expect(page.getByRole('checkbox')).toBeFocused();
  await expect(page.getByRole('alert')).toContainText('Confirm the signer');
  await expect(page.locator('.clip-total')).toHaveText('00');
  await expect(page.getByRole('button', { name: 'Finish recording', exact: true })).toHaveCount(0);
  await page.getByRole('checkbox').check();
  await expect(page.locator('#capture-status')).toHaveText('Preview only. Select Start recording to save a clip.');
});
