export const MEANINGS = [
  ['E01', 'Hello.'], ['E02', 'Thank you.'], ['E03', 'Please.'],
  ['E04', 'Yes.'], ['E05', 'No.'], ['E06', 'I need help.'],
  ['E07', 'I understand.'], ['E08', 'I do not understand.'],
  ['E09', 'Please repeat.'], ['E10', 'Please sign more slowly.'],
  ['E11', 'How are you?'], ['E12', 'I am fine.'],
] as const;

export const MAX_DURATION_MS = 10_000;
export const MAX_CLIP_BYTES = 8 * 1024 * 1024;
export const MAX_SESSION_BYTES = 64 * 1024 * 1024;
export const MAX_CLIPS = 12;
export const UNKNOWN_ID = 'unknown';

export interface RecordingDetails {
  signerId: string;
  permissionReference: string;
  meaningId: string;
  acknowledged: boolean;
}

export interface Clip {
  id: string;
  blob: Blob;
  url: string;
  durationMs: number;
  recordedAt: string;
  sha256: string;
  fileName: string;
  details: RecordingDetails;
  settings: { width: number | null; height: number | null; frameRate: number | null };
}

export function validateDetails(details: RecordingDetails): string | null {
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(details.signerId)) {
    return 'Enter a signer code using letters, numbers, underscores or hyphens.';
  }
  if (!/^[A-Za-z0-9_.-]{1,100}$/.test(details.permissionReference)) {
    return 'Enter a recording permission reference, without names or contact details.';
  }
  if (details.meaningId !== UNKNOWN_ID && !MEANINGS.some(([id]) => id === details.meaningId)) {
    return 'Select one of the proposed meanings or an unsupported example.';
  }
  if (!details.acknowledged) return 'Confirm the signer has agreed to this local recording.';
  return null;
}

export function meaningLabel(id: string): string {
  return id === UNKNOWN_ID ? 'Unsupported / no signing' : MEANINGS.find(([key]) => key === id)?.[1] ?? 'Unknown label';
}

export function canAddClip(clips: Clip[], additionalBytes = 0): boolean {
  return clips.length < MAX_CLIPS && clips.reduce((sum, clip) => sum + clip.blob.size, 0) + additionalBytes <= MAX_SESSION_BYTES;
}

export function formatDuration(milliseconds: number): string {
  return `${(milliseconds / 1000).toFixed(1)}s`;
}

export function cameraError(error: unknown): string {
  const name = error instanceof Error || error instanceof DOMException ? error.name : '';
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return 'Camera permission was declined. Allow camera access in your browser, then try again.';
  }
  if (name === 'NotFoundError') return 'No camera was found. Connect a camera, then try again.';
  if (name === 'NotReadableError') return 'Your camera is busy. Close other camera apps, then try again.';
  return 'The camera could not start. Check your browser permissions and camera connection.';
}

export function createManifest(clips: Clip[]) {
  if (!clips.length) throw new Error('Record at least one clip before exporting.');
  const signers = new Set(clips.map(clip => clip.details.signerId));
  return {
    schema_version: 'neosignis.capture.v1',
    purpose: 'local_evaluation',
    language: 'ase',
    label_set: 'everyday-12-proposed-v1',
    label_review_status: 'pending_fluent_asl_review',
    training_authorized: false,
    rendering_authorized: false,
    exported_at: new Date().toISOString(),
    signer_count: signers.size,
    clips: clips.map(clip => ({
      id: clip.id,
      file: `clips/${clip.fileName}`,
      sha256: clip.sha256,
      bytes: clip.blob.size,
      mime_type: clip.blob.type,
      duration_ms: Math.round(clip.durationMs),
      recorded_at: clip.recordedAt,
      signer_id: clip.details.signerId,
      permission_reference: clip.details.permissionReference,
      local_recording_acknowledged: clip.details.acknowledged,
      rights_review_status: 'unreviewed',
      reference_review_status: 'pending',
      expected_intent: clip.details.meaningId === UNKNOWN_ID ? null : clip.details.meaningId,
      suggested_text: clip.details.meaningId === UNKNOWN_ID ? null : meaningLabel(clip.details.meaningId),
      split: 'unassigned',
      display_mirrored: true,
      recording_mirrored: false,
      audio_recorded: false,
      track_settings: clip.settings,
    })),
  };
}
