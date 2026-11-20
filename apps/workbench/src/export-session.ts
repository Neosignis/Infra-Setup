import JSZip from 'jszip';
import { createManifest, type Clip } from './domain';

export async function hashBlob(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}

export async function exportSession(clips: Clip[]): Promise<Blob> {
  const manifest = createManifest(clips);
  const zip = new JSZip();
  zip.file('manifest.json', JSON.stringify(manifest, null, 2));
  zip.file('README.txt', 'Private local ASL evaluation recordings. Labels and rights require review.\nTraining, distribution and likeness permission are not established by this export.\nKeep recordings out of Git history. Splits are deliberately unassigned.\n');
  for (const clip of clips) zip.file(`clips/${clip.fileName}`, await clip.blob.arrayBuffer());
  return zip.generateAsync({ type: 'blob', compression: 'STORE' });
}

export function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
