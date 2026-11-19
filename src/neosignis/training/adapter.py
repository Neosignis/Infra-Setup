"""Small residual adapter over a frozen ASL translation encoder; optional torch."""
import hashlib
import math


def build_adapter(hidden_size, rank=16):
    import torch
    if type(hidden_size) is not int or hidden_size < 1 or type(rank) is not int or not 1 <= rank <= hidden_size:
        raise ValueError('Positive hidden size and bounded adapter rank required')

    class ResidualAdapter(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.down = torch.nn.Linear(hidden_size, rank)
            self.up = torch.nn.Linear(rank, hidden_size)
            # The untrained adapter exactly preserves the baseline output.
            torch.nn.init.zeros_(self.up.weight)
            torch.nn.init.zeros_(self.up.bias)

        def forward(self, hidden):
            return hidden + self.up(torch.nn.functional.gelu(self.down(hidden)))

    return ResidualAdapter()


def freeze_base(model):
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
        parameter.grad = None


def select_training(dataset, tokenizer, *, count=8, max_frames=180, max_target_tokens=64):
    """A predeclared resource-bounded sample, independent of validation scores."""
    if dataset.manifest['publisher_split'] != 'train':
        raise ValueError('Fitting requires the publisher training split')
    if type(count) is not int or not 1 <= count <= 32:
        raise ValueError('Small experiment supports 1..32 training examples')
    candidates, excluded = [], []
    for index in range(len(dataset)):
        sample = dataset[index]
        frames, tokens = len(sample.features), len(tokenizer.encode(sample.text, truncation=False))
        reason = ('short_clip_pending_review' if frames < 16 else 'frame_budget' if frames > max_frames
                  else 'target_budget' if tokens > max_target_tokens else None)
        if reason:
            excluded.append({'id': sample.id, 'reason': reason})
        else:
            candidates.append((hashlib.sha256(('asl-adapter-pilot-v1:' + sample.id).encode()).hexdigest(), index))
    if len(candidates) < count:
        raise ValueError('Not enough complete candidates within the declared resource bounds')
    ordered = [index for _, index in sorted(candidates)]
    excluded.extend({'id': dataset[index].id, 'reason': 'outside_fixed_training_sample'} for index in ordered[count:])
    return ordered[:count], excluded


def encode_source(model, source):
    """Cache only frozen visual/prompt encoder outputs, never reference text."""
    import torch
    from .unisign_runtime import pose_embeddings
    with torch.no_grad():
        prepared = pose_embeddings(model, source)
        encoded = model.mt5_model.encoder(**prepared, return_dict=True).last_hidden_state.detach()
    return encoded, prepared['attention_mask'].detach()


def prepare_labels(tokenizer, texts, *, max_tokens=128):
    encoded = tokenizer(texts, padding=True, truncation=False, return_tensors='pt')
    if encoded['input_ids'].shape[1] > max_tokens:
        raise ValueError('Full target exceeds explicit budget; do not truncate')
    return encoded['input_ids'].masked_fill(encoded['attention_mask'] == 0, -100)


def decoder_loss(decoder, adapter, encoded, mask, labels):
    from transformers.modeling_outputs import BaseModelOutput
    return decoder(encoder_outputs=BaseModelOutput(last_hidden_state=adapter(encoded)),
                   attention_mask=mask, labels=labels, use_cache=False).loss


def fit_step(decoder, adapter, optimizer, encoded, mask, labels, *, max_grad_norm=1.0):
    import torch
    if any(p.requires_grad for p in decoder.parameters()):
        raise ValueError('Base decoder must be frozen')
    owned = {id(p) for group in optimizer.param_groups for p in group['params']}
    if owned != {id(p) for p in adapter.parameters()}:
        raise ValueError('Optimizer must own only adapter parameters')
    optimizer.zero_grad(set_to_none=True)
    loss = decoder_loss(decoder, adapter, encoded, mask, labels)
    if not bool(torch.isfinite(loss)):
        raise ValueError('Nonfinite training loss')
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(adapter.parameters(), max_grad_norm, error_if_nonfinite=True)
    optimizer.step()
    if any(p.grad is not None for p in decoder.parameters()):
        raise ValueError('Frozen decoder unexpectedly received gradients')
    return float(loss.detach()), float(norm)


def evaluate_loss(decoder, adapter, samples):
    import torch
    total, tokens, per_example = 0.0, 0, []
    with torch.no_grad():
        for sample in samples:
            loss = float(decoder_loss(decoder, adapter, sample['encoded'], sample['mask'], sample['labels']))
            count = int((sample['labels'] != -100).sum())
            if not math.isfinite(loss) or count < 1:
                raise ValueError('Invalid evaluation loss')
            per_example.append({'id': sample['id'], 'loss': loss, 'target_tokens': count})
            total += loss * count; tokens += count
    if tokens == 0:
        raise ValueError('Empty evaluation set')
    return {'token_weighted_cross_entropy': total / tokens, 'target_tokens': tokens, 'examples': per_example}


def generate_text(decoder, tokenizer, adapter, sample, *, max_new_tokens=48):
    import torch
    from transformers.modeling_outputs import BaseModelOutput
    with torch.no_grad():
        output = decoder.generate(encoder_outputs=BaseModelOutput(last_hidden_state=adapter(sample['encoded'])),
                                  attention_mask=sample['mask'], max_new_tokens=max_new_tokens, num_beams=1)
    ids = output[0].tolist()
    return {'text': tokenizer.decode(ids, skip_special_tokens=True),
            'output_limit_reached': tokenizer.eos_token_id not in ids[1:]}


def load_trained_adapter(path, *, expected_sha256, expected_base_sha256):
    """Restore a small hash-pinned tensor checkpoint for explicit offline use."""
    from pathlib import Path
    import torch
    from .how2sign import sha256_file
    path = Path(path)
    if not 0 < path.stat().st_size <= 1024**2 or sha256_file(path) != expected_sha256:
        raise ValueError('Adapter checkpoint size or hash mismatch')
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    if (checkpoint.get('schema_version') != 'neosignis.asl-encoder-adapter.v1'
            or checkpoint.get('base_checkpoint_sha256') != expected_base_sha256
            or type(checkpoint.get('hidden_size')) is not int or not 1 <= checkpoint['hidden_size'] <= 1024
            or type(checkpoint.get('rank')) is not int or not 1 <= checkpoint['rank'] <= 32):
        raise ValueError('Adapter metadata or base model mismatch')
    model = build_adapter(checkpoint['hidden_size'], checkpoint['rank'])
    weights = checkpoint['adapter_state_dict']
    if any(not isinstance(value, torch.Tensor) or value.dtype != torch.float32 or not bool(torch.isfinite(value).all())
           for value in weights.values()):
        raise ValueError('Invalid adapter weights')
    model.load_state_dict(weights, strict=True)
    model.eval()
    return model, checkpoint
