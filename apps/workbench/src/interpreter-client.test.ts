import { afterEach, describe, expect, it, vi } from 'vitest';
import { getMessage, researchStatus, submitMessage } from './interpreter-client';
const id = '12345678-1234-1234-1234-123456789abc';
afterEach(() => vi.unstubAllGlobals());
describe('experimental interpreter transport', () => {
  it('sends raw video without a selected meaning or signer label', async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id }) });
    vi.stubGlobal('fetch', request);
    const blob = new Blob(['video'], { type: 'video/webm' });
    expect(await submitMessage(blob)).toBe(id);
    expect(request.mock.calls[0][1].body).toBe(blob);
    expect(request.mock.calls[0][1].headers['X-Neosignis-Request']).toBe('1');
    expect(JSON.stringify(request.mock.calls[0][1])).not.toContain('meaning');
  });
  it('never accepts a purported verified translation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id, state: 'complete', result: { disposition: 'needs_review', candidate_text: 'Hello', translated_text: 'Hello', confidence: .99, quality_validated: true } }) }));
    await expect(getMessage(id)).rejects.toThrow('Unvalidated');
  });
  it('rejects an empty suggestion and nonnumeric timing', async () => {
    for (const override of [{ candidate_text: '' }, { elapsed_s: 'fast' }]) {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id, state: 'complete', result: { disposition: 'needs_review', candidate_text: 'Hello.', translated_text: null, confidence: null, quality_validated: false, ...override } }) }));
      await expect(getMessage(id)).rejects.toThrow('Unvalidated');
    }
  });
  it('does not confuse an available experiment with validated quality', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ available: true, busy: false, mode: 'experimental_buffered_video', quality_validated: false, confidence_calibrated: false }) }));
    expect((await researchStatus()).quality_validated).toBe(false);
  });
  it('gives a useful admission error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 429 }));
    await expect(submitMessage(new Blob(['video']))).rejects.toThrow('still processing');
  });
});
