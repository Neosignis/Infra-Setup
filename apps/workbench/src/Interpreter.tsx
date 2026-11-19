import { useEffect, useRef, useState } from 'react';
import { Icon, CameraIllustration } from './ContributorStudio';
import { cameraError } from './domain';
import { RecordingSession } from './recorder';
import { cancelMessage, getMessage, researchStatus, submitMessage, type Outcome, type ResearchStatus } from './interpreter-client';

const reasons: Record<string, string> = {
  framing: 'I could not see enough of your face, upper body and signing hands. Adjust the camera and try again.',
  no_clear_activity: 'I could not identify clear signing movement. Try again with the complete message.',
  too_short: 'Please record a complete message, including its beginning and end.',
  unfinished_message: 'The recording reached its limit. Please try a shorter complete message.',
  outside_pilot_scope: 'I could not interpret this within the everyday pilot scope. Please repeat a short everyday message.',
};
const phases: Record<string, string> = { loading_pose: 'Preparing the signing detector…', detecting: 'Checking signing activity and framing…', loading_model: 'Preparing the interpreter. The first message takes longer…', translating: 'Interpreting your message…' };

export default function Interpreter({ active, onStudio }: { active: boolean; onStudio: () => void }) {
  const [camera, setCamera] = useState<'off' | 'requesting' | 'on'>('off');
  const [recording, setRecording] = useState(false), [elapsed, setElapsed] = useState(0);
  const [clip, setClip] = useState<Blob | null>(null), [preview, setPreview] = useState('');
  const [status, setStatus] = useState<ResearchStatus | null>(null), [connection, setConnection] = useState('Checking local interpreter…');
  const [pending, setPending] = useState(false), [phase, setPhase] = useState(''), [outcome, setOutcome] = useState<Outcome | null>(null);
  const [error, setError] = useState(''), [reply, setReply] = useState(''), [shownReply, setShownReply] = useState('');
  const video = useRef<HTMLVideoElement>(null), stream = useRef<MediaStream | null>(null), session = useRef<RecordingSession | null>(null);
  const generation = useRef(0), mounted = useRef(true), job = useRef<string | null>(null), polling = useRef<ReturnType<typeof setTimeout> | null>(null);
  const submission = useRef(0);

  async function refresh() {
    try { const next = await researchStatus(); if (mounted.current) { setStatus(next); setConnection(next.available ? 'Experimental model connected' : 'Local model setup is incomplete'); } }
    catch { if (mounted.current) { setStatus(null); setConnection('Local interpreter is offline'); } }
  }
  function stopCamera() {
    generation.current += 1; session.current?.dispose(); session.current = null;
    stream.current?.getTracks().forEach(track => track.stop()); stream.current = null;
    setCamera('off'); setRecording(false);
  }
  useEffect(() => {
    mounted.current = true; void refresh();
    return () => { mounted.current = false; generation.current += 1; submission.current += 1; session.current?.dispose(); stream.current?.getTracks().forEach(t => t.stop()); if (polling.current) clearTimeout(polling.current); if (job.current) void cancelMessage(job.current).catch(() => {}); };
  }, []);
  useEffect(() => { if (!active) stopCamera(); }, [active]);
  useEffect(() => { if (video.current) { video.current.srcObject = stream.current; if (stream.current) void video.current.play().catch(() => {}); } }, [camera]);
  useEffect(() => { if (!clip) { setPreview(''); return; } const url = URL.createObjectURL(clip); setPreview(url); return () => URL.revokeObjectURL(url); }, [clip]);

  async function enableCamera() {
    setError('');
    if (!navigator.mediaDevices?.getUserMedia) { setError('Use a browser with camera support on localhost or HTTPS.'); return; }
    const current = ++generation.current; setCamera('requesting');
    try {
      const next = await navigator.mediaDevices.getUserMedia({ audio: false, video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 24, max: 30 }, facingMode: 'user' } });
      if (!mounted.current || current !== generation.current) { next.getTracks().forEach(t => t.stop()); return; }
      stream.current = next; setCamera('on');
    } catch (cause) { if (current === generation.current && mounted.current) { setCamera('off'); setError(cameraError(cause)); } }
  }
  function record() {
    if (!stream.current || recording || pending) return;
    setError(''); setOutcome(null); setClip(null); setElapsed(0);
    try {
      session.current = new RecordingSession(stream.current, (blob, duration) => {
        if (!mounted.current) return; setRecording(false);
        if (duration >= 29500) { setError('The recording limit was reached. Try a shorter complete message.'); return; }
        setClip(blob);
      }, message => { if (mounted.current) { setRecording(false); setError(message); } }, setElapsed,
      { maxDurationMs: 30000, maxBytes: 16 * 1024 * 1024 });
      session.current.start(); setRecording(true);
    } catch (cause) { setRecording(false); setError(cause instanceof Error ? cause.message : 'Recording could not start.'); }
  }
  async function poll(id: string) {
    try {
      const next = await getMessage(id);
      if (!mounted.current || job.current !== id) return;
      if (next.state === 'processing') { setPhase(phases[next.phase] || 'Processing your message…'); polling.current = setTimeout(() => void poll(id), 1200); return; }
      job.current = null; setPending(false); void refresh();
      if (next.state === 'complete') setOutcome(next.result);
      else if (next.state === 'failed') setError('I could not interpret this recording. Check your framing and try again.');
    } catch (cause) { if (mounted.current && job.current === id) { setPending(false); job.current = null; setError(cause instanceof Error ? cause.message : 'Connection interrupted.'); } }
  }
  async function interpret() {
    if (!clip || pending || !status?.available) return;
    const attempt = ++submission.current;
    setPending(true); setError(''); setOutcome(null); setPhase('Sending your recording to the local interpreter…');
    try { const id = await submitMessage(clip); if (!mounted.current || attempt !== submission.current) { void cancelMessage(id).catch(() => {}); return; } job.current = id; void poll(id); }
    catch (cause) { if (mounted.current && attempt === submission.current) { setPending(false); setError(cause instanceof Error ? cause.message : 'Submission failed.'); } }
  }
  function clear() {
    submission.current += 1;
    if (polling.current) clearTimeout(polling.current);
    if (job.current) void cancelMessage(job.current).catch(() => {});
    job.current = null; setPending(false); setClip(null); setOutcome(null); setError(''); void refresh();
  }

  return <div className="app-shell interpreter-shell">
    <a className="skip-link" href="#main">Skip to interpreter</a>
    <aside className="sidebar" aria-label="Interpreter navigation">
      <a className="brand" href="#interpreter"><span className="brand-mark"><Icon name="camera" size={26} /></span><span>neosignis<span className="brand-subtitle">INTERPRETER</span></span></a>
      <div className="workspace-label">YOUR CONVERSATION</div>
      <nav><button className="nav-item active" aria-current="page"><Icon name="camera" /> Interpreter</button><button className="nav-item" onClick={onStudio}><Icon name="clips" /> Contributor Studio</button></nav>
      <div className="sidebar-note"><span className="eyebrow">ONE ENGINE. HUMAN CONNECTION.</span><p>Your hands.<br />Your message.</p><div className="small-rule" /><span>ASL → English · Local experiment</span></div>
      <div className="local-label"><span className="status-dot" /> Processed on this computer</div>
    </aside>
    <div className="main-shell"><header className="topbar"><span>Neosignis <span className="topbar-slash">/</span> Interpreter</span><span className="build-badge">EXPERIMENTAL <span>MESSAGE BY MESSAGE</span></span></header>
      <main id="main">
        <div className="page-heading"><div><div className="eyebrow">MAKE ROOM FOR YOUR MESSAGE</div><h1>Sign. Be understood.</h1><p>Record a complete ASL message and try an English interpretation.</p></div><span className="language-pill"><span>ASL</span> American Sign Language</span></div>
        <div className="scope-banner"><Icon name="info" /><p><strong>Early model experiment.</strong> Translations are unverified and processing is slower than a live conversation. Please check any suggestion before relying on it.</p></div>
        {error && <div className="feedback error" role="alert"><Icon name="info" />{error}</div>}
        <div className="workbench-grid interpreter-grid">
          <section aria-label="Sign a message"><div className="panel camera-panel">
            <div className="panel-topline"><span className="panel-title"><Icon name="camera" /> Your signing space</span><span className="state-pill">{recording ? 'Recording message' : camera === 'on' ? 'Camera on' : camera === 'requesting' ? 'Waiting for camera permission' : 'Camera off'}</span></div>
            <div className="camera-stage">
              <video ref={video} autoPlay muted playsInline className="live-video" hidden={camera !== 'on'} aria-label="Interpreter camera preview" />
              {camera !== 'on' ? <div className="camera-empty"><CameraIllustration /><h2>A little space for both hands.</h2><p>Keep your face and upper body in frame.<br />Choose when to record and when to send.</p><button className="button primary" disabled={camera === 'requesting'} onClick={() => void enableCamera()}>{camera === 'requesting' ? 'Waiting for permission…' : 'Enable camera'}</button>{camera === 'requesting' && <button className="text-button" onClick={stopCamera}>Cancel camera request</button>}</div>
                : <><span className="preview-tag">MIRRORED PREVIEW · VIDEO ONLY</span><span className="stage-tip">Keep your face, upper body and signing hands visible</span>{recording && <span className="recording-clock">{(elapsed / 1000).toFixed(1)}s</span>}</>}
            </div>
            <div className="camera-toolbar"><span>Preview is not sent automatically</span>{camera === 'on' && <button className="text-button" onClick={stopCamera}>Turn camera off</button>}</div>
            <div className="capture-controls"><div className="record-action"><div><span className="eyebrow">ONE COMPLETE MESSAGE</span><p>Start recording, sign, then finish. No meaning selection.</p></div><button className={`button ${recording ? 'stop' : 'primary'}`} disabled={camera !== 'on' || pending} onClick={() => recording ? session.current?.stop() : record()}>{recording ? 'Finish message' : 'Record a message'}</button></div></div>
          </div>
          {clip && <div className="panel interpreter-recording"><div><h2>Your recorded message</h2><p>Review before sending to the local model.</p></div><video controls playsInline src={preview || undefined} aria-label="Message recording" /><div className="interpreter-actions"><button className="button primary" onClick={() => void interpret()} disabled={pending || !status?.available}>Interpret message</button><button className="button" onClick={clear}>{pending ? 'Cancel and clear' : 'Discard message'}</button></div></div>}
          </section>
          <aside className="details-column" aria-label="Interpretation and reply">
            <div className="panel engine-panel"><div className="engine-heading"><span className="panel-title">Local interpreter</span><button className="icon-button" aria-label="Refresh interpreter connection" onClick={() => void refresh()}><Icon name="refresh" /></button></div><p className="interpreter-connection">{connection}</p><span className="muted-tag">{status?.busy ? 'Processing another message' : 'No calibrated confidence score yet'}</span></div>
            <div className="panel interpretation-panel" aria-live="polite" aria-busy={pending}><span className="eyebrow">ASL → ENGLISH</span><h2>Your message in words</h2>
              {pending ? <><div className="processing-indicator" /><p role="status">{phase}</p><p className="field-help">Processing can take a minute or longer, especially for the first message.</p></>
                : outcome?.disposition === 'needs_review' ? <><span className="result-label">Unverified suggestion</span><p className="interpreted-text">{outcome.candidate_text}</p><p>Please verify the meaning. The model can make mistakes.</p><button className="text-button" onClick={clear}>Try another message</button></>
                : outcome ? <><span className="result-label">Please clarify</span><p>{reasons[outcome.reason] || 'I could not interpret that reliably. Please try again.'}</p><button className="text-button" onClick={clear}>Try again</button></>
                : <p>Record and submit your message. A suggestion or clarification request will appear here.</p>}
              {outcome?.elapsed_s !== undefined && <p className="field-help">Processing time: {outcome.elapsed_s.toFixed(1)} seconds</p>}
            </div>
            <div className="panel reply-panel"><span className="eyebrow">YOUR RESPONSE</span><h2>Keep the conversation going.</h2><label className="field-label" htmlFor="typed-reply">Type a reply</label><textarea id="typed-reply" value={reply} maxLength={500} onChange={event => setReply(event.target.value)} placeholder="Write a response for your conversation partner…" /><button className="button" disabled={!reply.trim()} onClick={() => setShownReply(reply.trim())}>Show my reply</button>{shownReply && <p className="reply-text" aria-live="polite">{shownReply}</p>}<p className="field-help">Replies are shown as text. Signed playback is not available yet.</p></div>
          </aside>
        </div>
        <details className="pilot-scope"><summary>Everyday pilot scope</summary><p>Greeting, thanks, yes/no, asking for help, understanding, repetition, slower signing and wellbeing. These are a draft evaluation scope, not validated language coverage.</p><p>Activity detection uses a movement heuristic. Movement alone does not prove that a message is ASL.</p></details>
        <footer><span>NEOSIGNIS · HUMAN CONNECTION</span><span>Recordings are processed on this computer and are not saved by the interpreter.</span></footer>
      </main>
    </div>
  </div>;
}
