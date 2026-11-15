export interface Capability {
  language: 'ase' | 'nsi';
  recognize: boolean;
  render: boolean;
  approved: boolean;
  model_version: string | null;
  scope: string;
}

export type EngineState =
  | { state: 'checking' }
  | { state: 'offline'; message: string }
  | { state: 'connected'; languages: Capability[] };

export async function checkEngine(signal?: AbortSignal): Promise<EngineState> {
  try {
    const response = await fetch('/engine/v1/capabilities', { signal, cache: 'no-store' });
    if (!response.ok) {
      return { state: 'offline', message: response.status === 401
        ? 'The local API needs its development session. Start the demo with the launcher.'
        : 'The API is not ready. You can still capture and review local clips.' };
    }
    const body: unknown = await response.json();
    if (!body || typeof body !== 'object' || !('languages' in body) || !Array.isArray(body.languages)) {
      throw new Error('Invalid capability response');
    }
    const languages = body.languages as Capability[];
    if (languages.some(item => !item || !['ase', 'nsi'].includes(item.language)
      || typeof item.recognize !== 'boolean' || typeof item.render !== 'boolean'
      || typeof item.approved !== 'boolean'
      || ((item.recognize || item.render) && (!item.approved || !item.model_version)))) {
      throw new Error('Invalid capability response');
    }
    return { state: 'connected', languages };
  } catch (error) {
    if (signal?.aborted) throw error;
    return { state: 'offline', message: 'The local API is offline. Camera capture works independently.' };
  }
}
