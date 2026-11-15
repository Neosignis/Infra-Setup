import { Blob as NodeBlob } from 'node:buffer';
import { webcrypto } from 'node:crypto';
import JSZip from 'jszip';
import { afterEach, expect, it, vi } from 'vitest';
import { exportSession, hashBlob } from './export-session';
import type { Clip } from './domain';

afterEach(() => vi.unstubAllGlobals());
it('exports real clip bytes and a verifiable manifest without granting training rights', async () => {
  vi.stubGlobal('Blob', NodeBlob); vi.stubGlobal('crypto', webcrypto);
  const blob = new Blob(['private-test-video'], { type: 'video/webm' });
  const sha256 = await hashBlob(blob);
  expect(sha256).toMatch(/^[a-f0-9]{64}$/);
  const clip: Clip = { id: 'test', blob, url: 'blob:test', durationMs: 1000, recordedAt: '2026-11-14T10:00:00Z', sha256, fileName: 'test.webm', details: { signerId: 'test', permissionReference: 'test-permission', meaningId: 'E01', acknowledged: true }, settings: { width: null, height: null, frameRate: null } };
  const zip = await JSZip.loadAsync(await (await exportSession([clip])).arrayBuffer());
  expect(await zip.file('clips/test.webm')!.async('string')).toBe('private-test-video');
  const manifest = JSON.parse(await zip.file('manifest.json')!.async('string'));
  expect(manifest.clips[0].sha256).toBe(sha256);
  expect(manifest.training_authorized).toBe(false);
});
