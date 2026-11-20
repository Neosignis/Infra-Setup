import { describe, expect, it } from 'vitest';
import { canAddClip, createManifest, MAX_CLIPS, MEANINGS, validateDetails, type Clip, type RecordingDetails } from './domain';

const valid: RecordingDetails = { signerId: 'signer-001', permissionReference: 'permission-001', meaningId: 'E01', acknowledged: true };
const clip = (): Clip => ({ id: 'fixture', blob: new Blob(['fixture']), url: 'blob:fixture', durationMs: 1000, recordedAt: '2026-11-14T10:00:00Z', sha256: 'a'.repeat(64), fileName: 'fixture.webm', details: { ...valid }, settings: { width: 1280, height: 720, frameRate: 30 } });

describe('capture metadata', () => {
  it('contains twelve unique proposed meaning labels', () => expect(new Set(MEANINGS.map(([id]) => id)).size).toBe(12));
  it('accepts explicit local recording details', () => expect(validateDetails(valid)).toBeNull());
  it.each([{ signerId: '' }, { signerId: 'name@example.com' }, { permissionReference: '' }, { acknowledged: false }, { meaningId: 'unreviewed-model-label' }])('rejects incomplete/invalid details %j', change => expect(validateDetails({ ...valid, ...change })).not.toBeNull());
  it('supports explicit negative examples', () => expect(validateDetails({ ...valid, meaningId: 'unknown' })).toBeNull());
  it('bounds the in-memory clip count', () => expect(canAddClip(Array.from({ length: MAX_CLIPS }, clip))).toBe(false));
  it('does not export an empty session', () => expect(() => createManifest([])).toThrow('at least one'));
  it('does not turn local permission into training/likeness approval', () => {
    const manifest = createManifest([clip()]);
    expect(manifest.training_authorized).toBe(false);
    expect(manifest.rendering_authorized).toBe(false);
    expect(manifest.clips[0].rights_review_status).toBe('unreviewed');
    expect(manifest.clips[0].split).toBe('unassigned');
    expect(manifest.clips[0].recording_mirrored).toBe(false);
    expect(manifest.clips[0].display_mirrored).toBe(true);
  });
  it('exports an unknown reference as null', () => {
    const recording = clip(); recording.details.meaningId = 'unknown';
    expect(createManifest([recording]).clips[0].expected_intent).toBeNull();
  });
});
