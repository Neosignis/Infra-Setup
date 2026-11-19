import { useEffect, useRef, useState, type ReactNode } from 'react';
import { cameraError, canAddClip, formatDuration, MAX_CLIPS, MAX_DURATION_MS, MEANINGS, meaningLabel, UNKNOWN_ID, validateDetails, type Clip, type RecordingDetails } from './domain';
import { checkEngine, type EngineState } from './engine';
import { downloadBlob, exportSession, hashBlob } from './export-session';
import { RecordingSession } from './recorder';

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    camera: <><path d="M14 5h-4L8 8H4v11h16V8h-4z" /><circle cx="12" cy="13" r="3" /></>,
    clips: <><rect x="4" y="4" width="16" height="16" rx="3" /><path d="m10 8 6 4-6 4z" /></>,
    arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
    download: <><path d="M12 3v12m-4-4 4 4 4-4M5 16v5h14v-5" /></>,
    shield: <><path d="m12 3 8 3v6c0 4-8 9-8 9s-8-5-8-9V6z" /><path d="m8 12 3 3 5-6" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5" /><path d="M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1" /></>,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v1" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.info}</svg>;
}

export function CameraIllustration() {
  return <svg className="camera-illustration" viewBox="0 0 480 310" fill="none" aria-hidden="true">
    <path d="M108 82V48h40m184 0h40v34M108 228v34h40m184 0h40v-34" stroke="#8ba99a" strokeWidth="2" strokeLinecap="round" />
    <ellipse cx="240" cy="288" rx="126" ry="12" fill="#2c4c40" />
    <path d="M161 276v-62c0-38 34-61 79-61s79 23 79 61v62" fill="#3c6555" stroke="#90b29e" strokeWidth="1.5" />
    <path d="M214 148v24c12 11 40 11 52 0v-24" fill="#24483a" stroke="#90b29e" strokeWidth="1.5" />
    <rect x="201" y="61" width="78" height="100" rx="38" fill="#24483a" stroke="#b0cebc" strokeWidth="1.5" />
    <path d="M202 99c-4-36 10-53 40-53 28 0 43 19 38 54l-12-27c-22 16-39 10-51 5l-15 21Z" fill="#759b84" />
    <path d="M221 111h1m35 0h1m-27 24c5 4 13 4 18 0" stroke="#b0cebc" strokeWidth="2.5" strokeLinecap="round" />
    <path d="m174 244-27-36-8-44c-1-6 6-9 9-3l10 22-4-42c0-8 8-8 9-1l6 34 1-43c0-7 8-7 8 0l3 43 7-34c1-6 8-4 7 2l-6 47 9-13c4-5 10 0 7 6l-12 25-6 31" fill="#24483a" stroke="#b0cebc" strokeWidth="1.5" strokeLinejoin="round" />
    <path d="m306 244 27-36 8-44c1-6-6-9-9-3l-10 22 4-42c0-8-8-8-9-1l-6 34-1-43c0-7-8-7-8 0l-3 43-7-34c-1-6-8-4-7 2l6 47-9-13c-4-5-10 0-7 6l12 25 6 31" fill="#24483a" stroke="#b0cebc" strokeWidth="1.5" strokeLinejoin="round" />
    <path d="M139 287c8-25 13-43 25-54l28 7 17 47m62 0 17-47 28-7c12 11 17 29 25 54" fill="#608c73" stroke="#90b29e" strokeWidth="1.5" />
    <circle cx="240" cy="109" r="62" stroke="#729780" strokeDasharray="3 7" opacity=".55" />
  </svg>;
}

export default function ContributorStudio({ active = true, onInterpreter = () => { window.location.hash = 'interpreter'; } }: { active?: boolean; onInterpreter?: () => void }) {
  const [view, setView] = useState<'capture' | 'clips'>('capture');
  const [camera, setCamera] = useState<'off' | 'requesting' | 'on'>('off');
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [clips, setClips] = useState<Clip[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [notice, setNotice] = useState('');
  const [engine, setEngine] = useState<EngineState>({ state: 'checking' });
  const [details, setDetails] = useState<RecordingDetails>({ signerId: '', permissionReference: '', meaningId: 'E01', acknowledged: false });
  const video = useRef<HTMLVideoElement>(null);
  const signerInput = useRef<HTMLInputElement>(null);
  const permissionInput = useRef<HTMLInputElement>(null);
  const agreementInput = useRef<HTMLInputElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const session = useRef<RecordingSession | null>(null);
  const cameraGeneration = useRef(0);
  const clipsRef = useRef<Clip[]>([]);
  const mounted = useRef(true);
  const selected = clips.find(clip => clip.id === selectedId) || null;
  const invalidDetails = validateDetails(details);
  const busy = recording || processing;
  const asl = engine.state === 'connected' ? engine.languages.find(item => item.language === 'ase') : null;

  useEffect(() => {
    if (!active) {
      session.current?.dispose(); cameraGeneration.current += 1;
      stream.current?.getTracks().forEach(track => track.stop()); stream.current = null;
      setCamera('off'); setRecording(false);
    }
  }, [active]);

  useEffect(() => { clipsRef.current = clips; }, [clips]);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    void checkEngine(controller.signal).then(setEngine).catch(() => {});
    return () => {
      mounted.current = false;
      cameraGeneration.current += 1;
      controller.abort();
      session.current?.dispose();
      stream.current?.getTracks().forEach(track => track.stop());
      clipsRef.current.forEach(clip => URL.revokeObjectURL(clip.url));
    };
  }, []);

  useEffect(() => {
    if (video.current) {
      video.current.srcObject = stream.current;
      if (stream.current) void video.current.play().catch(() => {});
    }
  }, [camera, view]);

  useEffect(() => {
    if (!clips.length) return;
    const onClose = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', onClose);
    return () => window.removeEventListener('beforeunload', onClose);
  }, [clips.length]);

  async function startCamera() {
    setMessage('');
    if (!navigator.mediaDevices?.getUserMedia) {
      setMessage('Camera access needs a supported browser on localhost or HTTPS.');
      return;
    }
    const generation = ++cameraGeneration.current;
    setCamera('requesting');
    try {
      const next = await navigator.mediaDevices.getUserMedia({ audio: false, video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' } });
      if (!mounted.current || generation !== cameraGeneration.current) {
        next.getTracks().forEach(track => track.stop());
        return;
      }
      stream.current = next;
      setCamera('on');
      setNotice('Camera is on. Only an explicit recording creates a local clip.');
    } catch (error) {
      if (!mounted.current || generation !== cameraGeneration.current) return;
      setCamera('off');
      setMessage(cameraError(error));
    }
  }

  function stopCamera() {
    cameraGeneration.current += 1;
    if (recording) session.current?.stop();
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
    setCamera('off');
    setNotice('Camera is off. Your local clips remain in this tab.');
  }

  function startRecording() {
    if (!stream.current || !canAddClip(clipsRef.current) || busy) return;
    if (invalidDetails) {
      setMessage(`Before recording: ${invalidDetails}`);
      const missing = [signerInput.current, permissionInput.current, agreementInput.current].find(input => input && !input.validity.valid);
      missing?.focus();
      return;
    }
    setMessage(''); setNotice(''); setElapsed(0);
    const captureDetails = { ...details };
    const settings = stream.current.getVideoTracks()[0]?.getSettings() || {};
    try {
      session.current = new RecordingSession(stream.current, (blob, durationMs) => {
        setRecording(false);
        setProcessing(true);
        void hashBlob(blob).then(sha256 => {
          if (!mounted.current) return;
          if (!canAddClip(clipsRef.current, blob.size)) throw new Error('This session is full. Download and clear clips before recording more.');
          const id = crypto.randomUUID();
          const clip: Clip = {
            id, blob, sha256, url: URL.createObjectURL(blob), durationMs,
            recordedAt: new Date().toISOString(),
            fileName: `${id}.${blob.type.includes('mp4') ? 'mp4' : 'webm'}`,
            details: captureDetails,
            settings: { width: settings.width ?? null, height: settings.height ?? null, frameRate: settings.frameRate ?? null },
          };
          clipsRef.current = [...clipsRef.current, clip];
          setClips(clipsRef.current);
          setSelectedId(id);
          setView('clips');
          setNotice('Recording saved in this tab. Play it below to review, then download the session ZIP.');
        }).catch(error => {
          if (mounted.current) setMessage(error instanceof Error ? error.message : 'The clip could not be prepared.');
        }).finally(() => { if (mounted.current) setProcessing(false); });
      }, error => {
        if (!mounted.current) return;
        setRecording(false); setProcessing(false); setMessage(error);
      }, setElapsed);
      session.current.start();
      setRecording(true);
    } catch (error) {
      session.current?.dispose();
      setRecording(false);
      setMessage(error instanceof Error ? error.message : 'Recording could not start.');
    }
  }

  function removeClip(id: string) {
    const removed = clipsRef.current.find(clip => clip.id === id);
    if (removed) URL.revokeObjectURL(removed.url);
    clipsRef.current = clipsRef.current.filter(clip => clip.id !== id);
    setClips(clipsRef.current);
    if (selectedId === id) setSelectedId(clipsRef.current.at(-1)?.id || null);
    setNotice('Clip discarded from this tab.');
  }

  async function download() {
    if (!clips.length || exporting || busy) return;
    setExporting(true); setMessage('');
    try {
      const archive = await exportSession(clips);
      downloadBlob(archive, `neosignis-local-session-${new Date().toISOString().replace(/[:.]/g, '-')}.zip`);
      setNotice('Your browser started the private session download. Keep this ZIP out of GitHub.');
    } catch {
      setMessage('The session could not be exported. Your clips remain available in this tab.');
    } finally { setExporting(false); }
  }

  async function refreshEngine() {
    setEngine({ state: 'checking' });
    const next = await checkEngine();
    if (mounted.current) setEngine(next);
  }

  return <div className="app-shell">
    <a className="skip-link" href="#studio-main">Skip to contributor studio</a>
    <aside className="sidebar" aria-label="Workbench navigation">
      <a href="#studio-main" className="brand" onClick={() => setView('capture')} aria-label="Neosignis contributor studio">
        <span className="brand-mark"><svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M8 23V9l16 14V9M8 17l7-8m2 14 7-8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
        <span>neosignis<span className="brand-subtitle">CONTRIBUTOR STUDIO</span></span>
      </a>
      <div className="workspace-label">LOCAL WORKSPACE <span>01</span></div>
      <nav>
        <button className="nav-item" onClick={onInterpreter}><Icon name="arrow" /> Interpreter</button>
        <button className={`nav-item ${view === 'capture' ? 'active' : ''}`} aria-current={view === 'capture' ? 'page' : undefined} onClick={() => setView('capture')}><Icon name="camera" /> Camera capture <span className="nav-arrow">↗</span></button>
        <button className={`nav-item ${view === 'clips' ? 'active' : ''}`} aria-current={view === 'clips' ? 'page' : undefined} onClick={() => setView('clips')}><Icon name="clips" /> Session clips <span className="nav-count">{clips.length}</span></button>
      </nav>
      <div className="sidebar-note"><span className="eyebrow">ONE ENGINE. HUMAN CONNECTION.</span><p>Start with real signing.<br />Build with clear evidence.</p><div className="small-rule" /><span>ASL first · Everyday meanings</span></div>
      <div className="local-label"><span className="status-dot" /> Runs on your computer</div>
    </aside>

    <div className="main-shell">
      <header className="topbar"><span>Neosignis Interpreter <span className="topbar-slash">/</span> <strong>Foundation</strong></span><span className="build-badge">BUILD 01 <span>LOCAL PREVIEW</span></span></header>
      <main id="studio-main">
        <div className="page-heading"><div><div className="eyebrow">THE FIRST EXCHANGE STARTS HERE</div><h1>{view === 'capture' ? 'Capture a signing sample.' : 'Review your session.'}</h1><p>{view === 'capture' ? 'One meaning at a time. Your camera, your space, your control.' : 'Play back each recording before you keep it. Everything stays local.'}</p></div><span className="language-pill"><span>ASL</span> American Sign Language</span></div>

        <div className="scope-banner"><Icon name="info" size={18} /><p><strong>Contributor Studio · Dataset and evaluation recordings.</strong> Meaning choices label recordings for review. They are not predictions. Use Interpreter to try the experimental model.</p></div>

        {message && <div className="feedback error" role="alert"><Icon name="info" /><span>{message}</span><button className="icon-button" onClick={() => setMessage('')} aria-label="Dismiss error"><Icon name="close" size={16} /></button></div>}
        <div className="sr-only" role="status" aria-live="polite">{notice}</div>

        <div className="workbench-grid">
          <section className="capture-column" aria-label={view === 'capture' ? 'Camera capture' : 'Recording review'}>
            {view === 'capture' ? <>
              <div className="panel camera-panel">
                <div className="panel-topline"><span className="panel-title"><Icon name="camera" size={18} /> Camera preview</span><span className={`state-pill ${camera === 'on' ? 'connected' : ''}`}><span className="status-dot" />{recording ? 'Recording' : camera === 'on' ? 'Camera on' : camera === 'requesting' ? 'Waiting for permission' : 'Camera off'}</span></div>
                <div className={`camera-stage ${camera === 'on' ? 'is-live' : ''}`}>
                  <video ref={video} autoPlay playsInline muted className="live-video" aria-label="Live camera preview" hidden={camera !== 'on'} />
                  {camera === 'on' ? <><div className="live-framing" /><span className="preview-tag">MIRRORED PREVIEW · VIDEO ONLY</span><span className="stage-tip">Keep your face, upper body and both hands in frame</span></> : <div className="camera-empty"><CameraIllustration /><h2>A little space for both hands.</h2><p>Face the camera with your upper body visible.<br />Use steady light and a clear background.</p><button className="button primary light" onClick={startCamera} disabled={camera === 'requesting'}><Icon name="camera" size={18} />{camera === 'requesting' ? 'Waiting for camera…' : 'Enable camera'}</button></div>}
                  {recording && <span className="recording-clock"><span />{(elapsed / 1000).toFixed(1)} / 10.0s</span>}
                </div>
                <div className="camera-toolbar"><span><Icon name="shield" size={16} /> Preview is never uploaded</span>{camera !== 'off' && <button className="text-button" onClick={stopCamera}>{camera === 'requesting' ? 'Cancel request' : 'Turn camera off'}</button>}<span className="toolbar-caption">Visual framing guide</span></div>
                <div className="capture-controls">
                <div className="record-action"><div><span className="eyebrow">ONE COMPLETE UTTERANCE</span><p>Start, sign naturally, then finish.<br /><span>Recording stops automatically at {MAX_DURATION_MS / 1000} seconds.</span></p></div>
                  {recording ? <button className="button stop" onClick={() => session.current?.stop()}><span className="stop-shape" /> Finish recording</button> : <button className="button primary" aria-describedby="capture-status" onClick={startRecording} disabled={camera !== 'on' || busy || !canAddClip(clips)}><span className="record-shape" />{processing ? 'Preparing clip…' : 'Start recording'}</button>}
                </div>
                <p id="capture-status" className="capture-status" role="status">{recording ? 'Recording now. Sign, then select Finish recording.' : processing ? 'Preparing your recording…' : camera !== 'on' ? 'Enable the camera, complete the session details, then start recording.' : invalidDetails ? `Preview only — nothing is being recorded. ${invalidDetails}` : !canAddClip(clips) ? 'Session full. Download and discard clips to record more.' : 'Preview only. Select Start recording to save a clip.'}</p>
                </div>
              </div>

            <div className="panel setup-panel"><div className="section-heading"><div><span className="step-number">01</span><h2>Set up this session</h2></div></div><p className="panel-description">Use a code for the signer. Keep names and contact details out of this workbench.</p>
              <label className="field-label" htmlFor="signer">Signer code</label><input ref={signerInput} required pattern="[A-Za-z0-9_\-]{1,64}" id="signer" value={details.signerId} maxLength={64} placeholder="e.g. signer-001" autoComplete="off" disabled={busy} onChange={event => setDetails({ ...details, signerId: event.target.value })} />
              <label className="field-label" htmlFor="permission">Recording permission reference</label><input ref={permissionInput} required pattern="[A-Za-z0-9_.\-]{1,100}" id="permission" value={details.permissionReference} maxLength={100} placeholder="e.g. consent-001" autoComplete="off" disabled={busy} onChange={event => setDetails({ ...details, permissionReference: event.target.value })} />
              <label className="consent-check"><input ref={agreementInput} id="recording-permission" required type="checkbox" checked={details.acknowledged} disabled={busy} onChange={event => setDetails({ ...details, acknowledged: event.target.checked })} /><span>The signer has agreed to this local evaluation recording.</span></label>
              <div className="session-facts"><span>Language<strong>ASL</strong></span><span>Audio<strong>Off</strong></span><span>Dataset split<strong>Unassigned</strong></span></div>
            </div>
              <div className="panel recording-panel">
                <div className="section-heading"><div><span className="step-number">02</span><h2>Choose the meaning</h2></div><span className="muted-tag">Proposed labels · review pending</span></div>
                <label className="field-label" htmlFor="meaning">What will the signer express?</label>
                <select id="meaning" value={details.meaningId} disabled={busy} onChange={event => setDetails({ ...details, meaningId: event.target.value })}>
                  {MEANINGS.map(([id, text]) => <option key={id} value={id}>{id} · {text}</option>)}
                  <option value={UNKNOWN_ID}>Unsupported meaning / no signing</option>
                </select>
                <p className="field-help">These are meaning labels, not word-by-word instructions. A fluent ASL reviewer must validate each example.</p>
              </div>
            </> : <div className="panel review-panel">
              <div className="panel-topline"><span className="panel-title"><Icon name="clips" size={18} /> Clip review</span><span className="muted-tag">{clips.length} / {MAX_CLIPS} local clips</span></div>
              {selected ? <><div className="saved-clip-banner" role="status"><Icon name="check" size={18} /> Recording saved in this tab. Play it below, or <button className="text-button" onClick={() => setView('capture')}>Record another clip</button>.</div><div className="playback-stage"><video controls playsInline preload="metadata" src={selected.url} aria-label="Recorded signing clip" /></div><div className="clip-detail"><div><span className="eyebrow">{selected.details.meaningId.toUpperCase()} · REVIEW PENDING</span><h2>{meaningLabel(selected.details.meaningId)}</h2><p>Signer {selected.details.signerId} · {formatDuration(selected.durationMs)} · {(selected.blob.size / 1024).toFixed(0)} KB</p></div><button className="text-button danger" disabled={busy || exporting} onClick={() => removeClip(selected.id)}>Discard clip</button></div><div className="clip-list">{clips.map((clip, index) => <button key={clip.id} className={`clip-row ${selected.id === clip.id ? 'selected' : ''}`} onClick={() => setSelectedId(clip.id)}><span className="clip-index">{String(index + 1).padStart(2, '0')}</span><span><strong>{meaningLabel(clip.details.meaningId)}</strong><small>{clip.details.signerId} · {clip.details.meaningId.toUpperCase()}</small></span><span>{formatDuration(clip.durationMs)}</span><Icon name="clips" size={18} /></button>)}</div></> : <div className="review-empty"><Icon name="clips" size={42} /><h2>Your first clip starts an exchange.</h2><p>Record a signing sample, then return here<br />to review it before downloading.</p><button className="button primary" onClick={() => setView('capture')}>Go to camera <Icon name="arrow" size={17} /></button></div>}
            </div>}

            <div className="privacy-note"><Icon name="shield" size={19} /><p><strong>Local by default.</strong> Video stays in this tab until you download it. Closing or refreshing the page clears the session. Recording permission is separate from training, publishing or likeness rights.</p></div>
          </section>

          <aside className="details-column" aria-label="Engine and export">
            <div className="panel engine-panel"><div className="engine-heading"><span className="panel-title">Engine connection</span><button className="icon-button" aria-label="Check engine connection" onClick={refreshEngine} disabled={engine.state === 'checking'}><Icon name="refresh" size={16} /></button></div><div className="engine-line"><span>Local API</span><span className={`connection-label ${engine.state === 'connected' ? 'green' : ''}`}><span className="status-dot" />{engine.state === 'checking' ? 'Checking' : engine.state === 'connected' ? 'Connected' : 'Offline'}</span></div><div className="engine-line"><span>ASL recognition</span><span className="connection-label">{asl?.recognize ? 'Provider available' : 'Use Interpreter experiment'}</span></div><p>{engine.state === 'offline' ? engine.message : asl?.recognize ? 'A provider is available. Camera-to-inference extraction is a separate integration step.' : 'This studio labels recordings. The separate Interpreter runs the local experimental model.'}</p></div>
            <div className="export-card"><div className="export-header"><span className="export-icon"><Icon name="download" /></span><span className="clip-total">{String(clips.length).padStart(2, '0')}</span></div><h2>Your local session</h2><p>{clips.length ? 'Download your clips with their labels, hashes and permission references.' : 'Each recording will appear here, ready to review and export.'}</p><button className="button export-button" onClick={download} disabled={!clips.length || exporting || busy}>{exporting ? 'Preparing download…' : 'Download session ZIP'}<Icon name="download" size={17} /></button><span className="export-footnote">Private recordings · Review required</span></div>
          </aside>
        </div>
        {notice && <div className="notice" aria-hidden="true"><Icon name="check" size={15} />{notice}</div>}
        <footer><span>NEOSIGNIS <span className="footer-dot">·</span> BUILT FOR COMMUNICATION ACCESS</span><span>Capture → Review → Evaluate → Interpret</span></footer>
      </main>
    </div>
  </div>;
}
