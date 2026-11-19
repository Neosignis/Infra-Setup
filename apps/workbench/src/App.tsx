import { useEffect, useState } from 'react';
import ContributorStudio from './ContributorStudio';
import Interpreter from './Interpreter';

export default function App() {
  const current = () => window.location.hash.startsWith('#studio') ? 'studio' : 'interpreter';
  const [mode, setMode] = useState(current);
  const [visitedStudio, setVisitedStudio] = useState(current() === 'studio');
  useEffect(() => {
    const change = () => { const next = current(); setMode(next); if (next === 'studio') setVisitedStudio(true); };
    window.addEventListener('hashchange', change);
    return () => window.removeEventListener('hashchange', change);
  }, []);
  const navigate = (next: string) => { window.location.hash = next; setMode(next); if (next === 'studio') setVisitedStudio(true); };
  return <>
    <div hidden={mode !== 'interpreter'} style={{ display: mode === 'interpreter' ? undefined : 'none' }}><Interpreter active={mode === 'interpreter'} onStudio={() => navigate('studio')} /></div>
    {visitedStudio && <div hidden={mode !== 'studio'} style={{ display: mode === 'studio' ? undefined : 'none' }}><ContributorStudio active={mode === 'studio'} onInterpreter={() => navigate('interpreter')} /></div>}
  </>;
}
