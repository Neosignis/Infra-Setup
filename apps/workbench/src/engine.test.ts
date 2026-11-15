import { afterEach, describe, expect, it, vi } from 'vitest';
import { checkEngine } from './engine';

afterEach(() => vi.unstubAllGlobals());
const capability = { language: 'ase', recognize: false, render: false, approved: false, model_version: null, scope: 'unavailable' };

describe('engine connection', () => {
  it('shows a connected API independently from model readiness', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ languages: [capability] }) }));
    const result = await checkEngine();
    expect(result.state).toBe('connected');
    if (result.state === 'connected') expect(result.languages[0].recognize).toBe(false);
  });
  it('handles an offline worker without inventing output', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    expect((await checkEngine()).state).toBe('offline');
  });
  it('reports an authentication mismatch', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    const result = await checkEngine();
    expect(result.state === 'offline' && result.message).toContain('development session');
  });
  it('rejects malformed or unapproved enabled capability data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ languages: [{ ...capability, recognize: true }] }) }));
    expect((await checkEngine()).state).toBe('offline');
  });
});
