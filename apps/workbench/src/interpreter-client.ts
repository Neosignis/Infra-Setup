export interface ResearchStatus { available: boolean; busy: boolean; mode: 'experimental_buffered_video'; quality_validated: false; confidence_calibrated: false }
export interface Outcome { disposition: 'abstained' | 'needs_review'; reason: string; candidate_text: string | null; translated_text: null; confidence: null; quality_validated: false; elapsed_s?: number; segments: { start_ms: number; end_ms: number }[] }
export interface Job { id: string; state: 'processing' | 'complete' | 'failed' | 'cancelled'; phase: string; result: Outcome | null; error?: string }
const headers = { 'X-Neosignis-Request': '1' };

export async function researchStatus(): Promise<ResearchStatus> {
  const response = await fetch('/research/status', { headers, cache: 'no-store' });
  if (!response.ok) throw new Error('Local interpreter is offline.');
  const data = await response.json();
  if (typeof data.available !== 'boolean' || typeof data.busy !== 'boolean' || data.mode !== 'experimental_buffered_video' || data.quality_validated !== false || data.confidence_calibrated !== false) throw new Error('Unrecognized interpreter status.');
  return data;
}
export async function submitMessage(blob: Blob): Promise<string> {
  const response = await fetch('/research/jobs', { method: 'POST', headers: { ...headers, 'Content-Type': blob.type || 'video/webm' }, body: blob });
  if (!response.ok) throw new Error(response.status === 429 ? 'Another message is still processing. Please wait.' : 'This message could not be submitted. Check the local interpreter connection.');
  const data = await response.json();
  if (typeof data.id !== 'string' || !/^[0-9a-f-]{36}$/.test(data.id)) throw new Error('Invalid message receipt.');
  return data.id;
}
export async function getMessage(id: string): Promise<Job> {
  const response = await fetch(`/research/jobs/${encodeURIComponent(id)}`, { headers, cache: 'no-store' });
  if (!response.ok) throw new Error('The message expired or the interpreter disconnected. Please try again.');
  const job = await response.json();
  if (job.id !== id || !['processing', 'complete', 'failed', 'cancelled'].includes(job.state)) throw new Error('Invalid message status.');
  if (job.state === 'complete') {
    const r = job.result;
    if (!r || !['abstained', 'needs_review'].includes(r.disposition) || r.confidence !== null || r.translated_text !== null || r.quality_validated !== false || (r.candidate_text !== null && (typeof r.candidate_text !== 'string' || r.candidate_text.length > 512))
      || (r.disposition === 'needs_review' && !r.candidate_text?.trim()) || (r.disposition === 'abstained' && r.candidate_text !== null)
      || (r.elapsed_s !== undefined && (typeof r.elapsed_s !== 'number' || !Number.isFinite(r.elapsed_s) || r.elapsed_s < 0))) throw new Error('Unvalidated output was rejected.');
  }
  return job;
}
export async function cancelMessage(id: string) {
  await fetch(`/research/jobs/${encodeURIComponent(id)}`, { method: 'DELETE', headers });
}
