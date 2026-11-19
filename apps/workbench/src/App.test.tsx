import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './ContributorStudio';

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
    expect(screen.getByText('Use Interpreter experiment')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start recording' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Download session/ })).toBeDisabled();
  });
  it('shows an actionable permission-denied message', async () => {
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockRejectedValue(new DOMException('declined', 'NotAllowedError')) } });
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Enable camera' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('permission was declined');
  });
  it('shows why preview has not recorded and focuses each missing prerequisite', async () => {
    const next = { getTracks: () => [{ stop: vi.fn() }] } as unknown as MediaStream;
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue(next) } });
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Enable camera' }));
    await screen.findByText('Camera on');
    const start = screen.getByRole('button', { name: 'Start recording' });
    expect(start).toBeEnabled();
    fireEvent.click(start);
    expect(screen.getByRole('alert')).toHaveTextContent('Before recording: Enter a signer code');
    expect(screen.getByLabelText('Signer code')).toHaveFocus();
    fireEvent.change(screen.getByLabelText('Signer code'), { target: { value: 'self-001' } });
    fireEvent.click(start);
    expect(screen.getByLabelText('Recording permission reference')).toHaveFocus();
    fireEvent.change(screen.getByLabelText('Recording permission reference'), { target: { value: 'self-test-001' } });
    fireEvent.click(start);
    expect(screen.getByRole('checkbox')).toHaveFocus();
    expect(screen.queryByRole('button', { name: 'Finish recording' })).not.toBeInTheDocument();
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
