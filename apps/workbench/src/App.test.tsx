import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ languages: [
    { language: 'ase', recognize: false, render: false, approved: false, model_version: null, scope: 'unavailable' },
  ] }) }));
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue();
});
afterEach(() => vi.unstubAllGlobals());

describe('local camera workbench', () => {
  it('distinguishes API connectivity from a trained recognizer', async () => {
    render(<App />);
    expect(await screen.findByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('Not installed')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start recording' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Download session/ })).toBeDisabled();
  });
  it('shows an actionable permission-denied message', async () => {
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockRejectedValue(new DOMException('declined', 'NotAllowedError')) } });
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Enable camera' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('permission was declined');
  });
  it('stops a stream that resolves after its permission request was cancelled', async () => {
    let resolve: (value: MediaStream) => void = () => {};
    const stopped = vi.fn();
    const next = { getTracks: () => [{ stop: stopped }] } as unknown as MediaStream;
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: () => new Promise<MediaStream>(r => { resolve = r; }) } });
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Enable camera' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel request' }));
    resolve(next);
    await waitFor(() => expect(stopped).toHaveBeenCalledTimes(1));
    expect(screen.getByText('Camera off')).toBeInTheDocument();
  });
  it('offers a real empty-review state without sample signing footage', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /Session clips/ }));
    expect(screen.getByText('Your first clip starts an exchange.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Recorded signing clip')).not.toBeInTheDocument();
  });
});
