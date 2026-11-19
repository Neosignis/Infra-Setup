"""Local tensor-only checkpoint verification; no network or upstream code imports."""
import hashlib
import os
from pathlib import Path
import re


def load_tensor_checkpoint(path, *, expected_sha256, expected_bytes):
    """Pin bytes before loading, CPU only, no unrestricted pickle fallback.

    A checksum establishes identity, not licensing or trust. The caller must
    obtain expected values from its reviewed asset record, never the same file.
    """
    import torch
    if not re.fullmatch('[0-9a-f]{64}', expected_sha256) or expected_bytes <= 0:
        raise ValueError('Expected publisher checksum and byte count are required')
    path = Path(path)
    # Use the same open file handle for hashing and deserialization.
    with path.open('rb') as source:
        if os.fstat(source.fileno()).st_size != expected_bytes:
            raise ValueError('Checkpoint byte count mismatch')
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024**2), b''):
            digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError('Checkpoint SHA256 mismatch')
        source.seek(0)
        checkpoint = torch.load(source, map_location='cpu', weights_only=True)
    state = checkpoint.get('model') if isinstance(checkpoint, dict) and 'model' in checkpoint else checkpoint
    if not isinstance(state, dict) or not state:
        raise ValueError('Expected nonempty state dictionary')
    for name, tensor in state.items():
        if not isinstance(name, str) or not isinstance(tensor, torch.Tensor):
            raise ValueError('State dictionary must contain named tensors only')
        if (tensor.is_floating_point() or tensor.is_complex()) and not torch.isfinite(tensor).all().item():
            raise ValueError('Nonfinite checkpoint weights')
    return state


def restore_model(model, path, *, expected_sha256, expected_bytes):
    """Validate all keys/shapes before mutating a separately supplied model."""
    state = load_tensor_checkpoint(path, expected_sha256=expected_sha256, expected_bytes=expected_bytes)
    current = model.state_dict()
    if set(current) != set(state) or any(current[k].shape != state[k].shape for k in current):
        raise ValueError('Checkpoint keys/shapes do not match the supplied architecture')
    model.load_state_dict(state, strict=True)
    return model
