import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MAX_CLIP_BYTES } from './domain';
import { RecordingSession } from './recorder';

class FakeRecorder {
  static instance: FakeRecorder;
  static isTypeSupported = () => true;
  state = 'inactive';
  mimeType = 'video/webm';
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor() { FakeRecorder.instance = this; }
  start() { this.state = 'recording'; }
  stop() { this.state = 'inactive'; this.onstop?.(); }
}

beforeEach(() => { vi.stubGlobal('MediaRecorder', FakeRecorder); vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
const stream = {} as MediaStream;

describe('bounded recording lifecycle', () => {
  it('automatically ends a recording at ten seconds', () => {
    const completed = vi.fn(), failed = vi.fn();
    const session = new RecordingSession(stream, completed, failed, vi.fn());
    session.start();
    FakeRecorder.instance.ondataavailable?.({ data: new Blob(['video-fixture']) });
    vi.advanceTimersByTime(10_100);
    expect(completed).toHaveBeenCalledTimes(1);
    expect(completed.mock.calls[0][1]).toBe(9_900);
    expect(failed).not.toHaveBeenCalled();
  });
  it('rejects empty recordings', () => {
    const completed = vi.fn(), failed = vi.fn();
    const session = new RecordingSession(stream, completed, failed, vi.fn());
    session.start(); vi.advanceTimersByTime(1000); session.stop();
    expect(completed).not.toHaveBeenCalled();
    expect(failed).toHaveBeenCalledWith(expect.stringContaining('empty'));
  });
  it('drops oversized data and preserves the failure state', () => {
    const completed = vi.fn(), failed = vi.fn();
    const session = new RecordingSession(stream, completed, failed, vi.fn());
    session.start();
    FakeRecorder.instance.ondataavailable?.({ data: new Blob([new Uint8Array(MAX_CLIP_BYTES + 1)]) });
    expect(failed).toHaveBeenCalledTimes(1);
    expect(completed).not.toHaveBeenCalled();
  });
  it('does not save discarded or unmounted recordings', () => {
    const completed = vi.fn(), failed = vi.fn();
    const session = new RecordingSession(stream, completed, failed, vi.fn());
    session.start();
    FakeRecorder.instance.ondataavailable?.({ data: new Blob(['video-fixture']) });
    session.dispose(); vi.advanceTimersByTime(11_000);
    expect(completed).not.toHaveBeenCalled(); expect(failed).not.toHaveBeenCalled();
  });
});
