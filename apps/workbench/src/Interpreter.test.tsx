import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Interpreter from './Interpreter';
import App from './App';

class FakeRecorder {
  static current: FakeRecorder;
  static isTypeSupported = () => true;
  state = 'inactive'; mimeType = 'video/webm';
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  constructor() { FakeRecorder.current = this; }
  start() { this.state = 'recording'; }
  stop() { this.state = 'inactive'; this.onstop?.(); }
}
const ready = { available: true, busy: false, mode: 'experimental_buffered_video', quality_validated: false, confidence_calibrated: false };
const id = '12345678-1234-1234-1234-123456789abc';
const stopped = vi.fn();
beforeEach(() => {
  window.location.hash = '';
  vi.stubGlobal('MediaRecorder', FakeRecorder);
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:test-recording') });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue();
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopped }] }) } });
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => ({ ok: true, json: async () => url.includes('/research/') ? ready : { languages: [] } })));
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

async function recordMessage() {
  fireEvent.click(screen.getByRole('button', { name: 'Enable camera' }));
  await screen.findByText('Camera on');
  const clock = vi.spyOn(performance, 'now').mockReturnValue(0);
  fireEvent.click(screen.getByRole('button', { name: 'Record a message' }));
  act(() => FakeRecorder.current.ondataavailable?.({ data: new Blob(['recorded-video'], { type: 'video/webm' }) }));
  clock.mockReturnValue(1400);
  fireEvent.click(screen.getByRole('button', { name: 'Finish message' }));
  await screen.findByRole('button', { name: 'Interpret message' });
  clock.mockRestore();
}

describe('Interpreter experience', () => {
  it('is the main screen and never asks for a meaning label', async () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: 'Sign. Be understood.' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Signer code')).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(await screen.findByText('Experimental model connected')).toBeInTheDocument();
  });
  it('preserves contributor details when switching screens', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Contributor Studio' }));
    fireEvent.change(screen.getByLabelText('Signer code'), { target: { value: 'saved-signer' } });
    fireEvent.click(screen.getByRole('button', { name: 'Interpreter' }));
    fireEvent.click(screen.getByRole('button', { name: 'Contributor Studio' }));
    expect(screen.getByLabelText('Signer code')).toHaveValue('saved-signer');
  });
  it('submits without labels and shows a qualified model suggestion', async () => {
    const request = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => ({ ok: true, json: async () => url.endsWith('/status') ? ready : init?.method === 'POST' ? { id } : { id, state: 'complete', result: { disposition: 'needs_review', candidate_text: 'Hello.', translated_text: null, confidence: null, quality_validated: false, elapsed_s: 2, segments: [] } } }));
    vi.stubGlobal('fetch', request);
    render(<Interpreter active onStudio={vi.fn()} />);
    await screen.findByText('Experimental model connected');
    await recordMessage();
    expect(request.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: 'Interpret message' }));
    expect(await screen.findByText('Unverified suggestion')).toBeInTheDocument();
    expect(screen.getByText('Hello.')).toBeInTheDocument();
    expect(request.mock.calls.find(([, init]) => init?.method === 'POST')?.[1].body).toBeInstanceOf(Blob);
  });
  it('shows clarification rather than guessed text for an abstention', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string, init?: RequestInit) => ({ ok: true, json: async () => url.endsWith('/status') ? ready : init?.method === 'POST' ? { id } : { id, state: 'complete', result: { disposition: 'abstained', candidate_text: null, translated_text: null, confidence: null, quality_validated: false, reason: 'framing', segments: [] } } })));
    render(<Interpreter active onStudio={vi.fn()} />);
    await screen.findByText('Experimental model connected'); await recordMessage();
    fireEvent.click(screen.getByRole('button', { name: 'Interpret message' }));
    expect(await screen.findByText('Please clarify')).toBeInTheDocument();
    expect(screen.queryByText('Unverified suggestion')).not.toBeInTheDocument();
  });
  it('stops the camera when leaving Interpreter', async () => {
    const { rerender } = render(<Interpreter active onStudio={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Enable camera' }));
    await screen.findByText('Camera on');
    rerender(<Interpreter active={false} onStudio={vi.fn()} />);
    await waitFor(() => expect(stopped).toHaveBeenCalled());
    expect(screen.getByText('Camera off')).toBeInTheDocument();
  });
  it('shows typed replies while disclosing signed playback is unavailable', () => {
    render(<Interpreter active onStudio={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Type a reply'), { target: { value: 'Please repeat that.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Show my reply' }));
    expect(screen.getByText('Please repeat that.', { selector: '.reply-text' })).toBeInTheDocument();
    expect(screen.getByText(/Signed playback is not available yet/)).toBeInTheDocument();
  });
});
