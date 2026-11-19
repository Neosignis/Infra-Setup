"""Offline pose-only experiment runner, using the pinned local source bundle.

Run in a dedicated CLI process; the foundation API does not import this module.
No network access occurs during model construction or inference.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

from .checkpoint import load_tensor_checkpoint

CODE_REVISION = 'eed438bcb49e30405cd6ccdfcccca330c134e830'
CHECKPOINT_SHA = '1bfd5f3312f04e4736f0a52f4ef9535916e6de9676a2a0d00c708748683fb00d'
CHECKPOINT_BYTES = 1186925007


def verified_bundle(root):
    root = Path(root).resolve()
    receipt = json.loads((root / 'acquisition.json').read_text())
    if receipt['code_revision'] != CODE_REVISION:
        raise ValueError('Unexpected source revision')
    records = {Path(a['file']).resolve(): a for a in receipt['assets']}
    for folder, names in [('source', ['models.py', 'deformable_attention_2d.py',
                                     'stgcn_layers/__init__.py', 'stgcn_layers/gcn_utils.py', 'stgcn_layers/stgcn_block.py']),
                          ('decoder', ['config.json', 'spiece.model', 'special_tokens_map.json', 'tokenizer_config.json'])]:
        for name in names:
            path = root / folder / name
            record = records.get(path.resolve())
            if record is None or path.stat().st_size != record['bytes']:
                raise ValueError('Missing/changed source or tokenizer asset')
            if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('Source/tokenizer hash mismatch')
    return root


def load_unisign(root, *, device='cpu'):
    root = verified_bundle(root)
    os.environ.setdefault('HF_HOME', str(root / 'hf-cache'))
    import torch
    from transformers import MT5Config, MT5ForConditionalGeneration, T5Tokenizer
    if device not in {'cpu', 'mps'} or (device == 'mps' and not torch.backends.mps.is_available()):
        raise ValueError('Requested local device is unavailable')
    # Keep all code/tokenizer construction local. No second 2.33 GB decoder
    # weight download: the SLT checkpoint must supply every architecture key.
    config = ModuleType('config')
    config.mt5_path = str(root / 'decoder')
    previous_config = sys.modules.get('config')
    sys.modules['config'] = config
    sys.path.insert(0, str(root / 'source'))
    try:
        spec = importlib.util.spec_from_file_location('neosignis_local_unisign', root / 'source/models.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
        if previous_config is None:
            sys.modules.pop('config', None)
        else:
            sys.modules['config'] = previous_config

    class LocalDecoderFactory:
        @staticmethod
        def from_pretrained(path):
            return MT5ForConditionalGeneration(MT5Config.from_pretrained(path, local_files_only=True))

    class LocalTokenizerFactory:
        @staticmethod
        def from_pretrained(path, **kwargs):
            return T5Tokenizer.from_pretrained(path, local_files_only=True, **kwargs)

    module.MT5ForConditionalGeneration = LocalDecoderFactory
    module.T5Tokenizer = LocalTokenizerFactory
    args = SimpleNamespace(hidden_dim=256, rgb_support=False, dataset='How2Sign', label_smoothing=0.0)
    # Meta tensors avoid allocating a duplicate random full-language model.
    with torch.device('meta'):
        model = module.Uni_Sign(args)
    state = load_tensor_checkpoint(root / 'how2sign_pose_only_slt.pth',
                                   expected_sha256=CHECKPOINT_SHA, expected_bytes=CHECKPOINT_BYTES)
    current = model.state_dict()
    if set(current) != set(state) or any(current[k].shape != state[k].shape for k in current):
        raise ValueError('Selected checkpoint does not completely match the pose-only architecture')
    model.load_state_dict(state, strict=True, assign=True)
    if any(p.is_meta for p in model.parameters()) or any(b.is_meta for b in model.buffers()):
        raise ValueError('Model still contains uninitialized meta tensors')
    model.eval()
    return model.to(device=device, dtype=torch.float32)


def pose_embeddings(model, source):
    """Execute the pose branch without the upstream target-text training cap."""
    import torch
    features, body = [], None
    for part in model.modes:
        projected = model.proj_linear[part](source[part]).permute(0, 3, 1, 2)
        value = model.gcn_modules[part](projected)
        if part == 'body':
            body = value
        else:
            anchor = {'left': -2, 'right': -1, 'face_all': 0}[part]
            value = value + body[:, :, :, anchor].unsqueeze(-1).detach()
        value = model.fusion_gcn_modules[part](value)
        features.append(value.mean(-1).transpose(1, 2))
    embeddings = model.pose_proj(torch.cat(features, dim=-1) + model.part_para)
    prompt = model.mt5_tokenizer(['Translate sign language video to English: '] * len(source['name_batch']),
                                 padding=True, truncation=False, return_tensors='pt').to(embeddings.device)
    prefix = model.mt5_model.encoder.embed_tokens(prompt['input_ids'])
    return {'inputs_embeds': torch.cat([prefix, embeddings], dim=1),
            'attention_mask': torch.cat([prompt['attention_mask'], source['attention_mask']], dim=1)}


def translate(model, source, *, max_new_tokens=80):
    import torch
    with torch.inference_mode():
        prepared = pose_embeddings(model, source)
        output = model.mt5_model.generate(**prepared, max_new_tokens=max_new_tokens, num_beams=1)
    return model.mt5_tokenizer.batch_decode(output, skip_special_tokens=True)


def translation_loss(model, source, sentences, *, max_target_tokens=512):
    """Full target text; never route through upstream forward's 50-token cap."""
    targets = model.mt5_tokenizer(sentences, padding=True, truncation=False, return_tensors='pt')
    if targets['input_ids'].shape[1] > max_target_tokens:
        raise ValueError('Target exceeds explicit budget; no silent truncation')
    labels = targets['input_ids'].masked_fill(targets['attention_mask'] == 0, -100)
    prepared = pose_embeddings(model, source)
    return model.mt5_model(**prepared, labels=labels.to(prepared['inputs_embeds'].device)).loss
