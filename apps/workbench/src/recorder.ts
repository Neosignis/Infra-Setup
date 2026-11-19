import { MAX_CLIP_BYTES, MAX_DURATION_MS } from './domain';

export function supportedMimeType(): string {
  if (typeof MediaRecorder === 'undefined') throw new Error('Recording is not supported by this browser. Try a recent Chrome, Edge or Safari browser.');
  return ['video/webm;codecs=vp8', 'video/webm', 'video/mp4'].find(type => MediaRecorder.isTypeSupported(type)) || '';
}

/** Owns bounded in-memory recording. It never sends data over the network. */
export class RecordingSession {
  private recorder: MediaRecorder;
  private chunks: Blob[] = [];
  private startedAt = 0;
  private stoppedAt: number | null = null;
  private timer: ReturnType<typeof setInterval> | undefined;
  private deadlineTimer: ReturnType<typeof setTimeout> | undefined;
  private disposed = false;
  private failed = false;
  private bytes = 0;

  constructor(
    stream: MediaStream,
    private onComplete: (blob: Blob, durationMs: number) => void,
    private onError: (message: string) => void,
    private onTick: (durationMs: number) => void,
    private limits = { maxDurationMs: MAX_DURATION_MS, maxBytes: MAX_CLIP_BYTES },
  ) {
    const mimeType = supportedMimeType();
    this.recorder = new MediaRecorder(stream, { ...(mimeType ? { mimeType } : {}), videoBitsPerSecond: 2_000_000 });
    this.recorder.ondataavailable = event => {
      if (this.disposed || this.failed || !event.data.size) return;
      this.bytes += event.data.size;
      if (this.bytes > this.limits.maxBytes) {
        this.fail('This clip exceeded the local size limit. Try a shorter recording.');
        return;
      }
      this.chunks.push(event.data);
    };
    this.recorder.onerror = () => this.fail('Recording failed. Your camera can stay open while you try again.');
    this.recorder.onstop = () => {
      this.clearTimer();
      if (this.disposed || this.failed) return;
      const durationMs = Math.max(0, (this.stoppedAt ?? performance.now()) - this.startedAt);
      const blob = new Blob(this.chunks, { type: this.recorder.mimeType || mimeType || 'video/webm' });
      this.chunks = [];
      if (!blob.size || durationMs < 100) {
        this.onError('The recording was empty or too short. Sign for at least a moment, then finish.');
        return;
      }
      if (durationMs > this.limits.maxDurationMs) {
        this.onError(`Recording exceeded ${this.limits.maxDurationMs / 1000} seconds. Keep this tab active and try again.`);
        return;
      }
      this.onComplete(blob, durationMs);
    };
  }

  start() {
    this.startedAt = performance.now();
    this.recorder.start(250);
    // Leave a small scheduling margin; never disguise an overlong clip by clamping metadata.
    this.deadlineTimer = setTimeout(() => this.stop(), this.limits.maxDurationMs - 100);
    this.timer = setInterval(() => {
      const elapsed = performance.now() - this.startedAt;
      this.onTick(Math.min(elapsed, this.limits.maxDurationMs));
      if (elapsed >= this.limits.maxDurationMs) this.stop();
    }, 100);
  }

  stop() {
    if (this.stoppedAt === null) this.stoppedAt = performance.now();
    this.clearTimer();
    if (this.recorder.state !== 'inactive') this.recorder.stop();
  }

  dispose() {
    this.disposed = true;
    this.stop();
    this.chunks = [];
  }

  private clearTimer() {
    if (this.timer !== undefined) clearInterval(this.timer);
    if (this.deadlineTimer !== undefined) clearTimeout(this.deadlineTimer);
    this.timer = undefined;
    this.deadlineTimer = undefined;
  }

  private fail(message: string) {
    if (this.failed || this.disposed) return;
    this.failed = true;
    this.stop();
    this.chunks = [];
    this.onError(message);
  }
}
