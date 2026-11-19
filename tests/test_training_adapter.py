"""Small local fixtures verify fitting mechanics, not ASL language accuracy."""
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from neosignis.training.adapter import build_adapter, freeze_base, select_training


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Optional torch adapter tests')
class AdapterTests(unittest.TestCase):
    def test_untrained_adapter_exactly_preserves_input_and_has_small_parameter_count(self):
        import torch
        torch.manual_seed(1)
        adapter = build_adapter(768, rank=16)
        sample = torch.randn(2, 9, 768)
        self.assertTrue(torch.equal(adapter(sample), sample))
        self.assertEqual(sum(p.numel() for p in adapter.parameters()), 25360)
        for rank in (0, 769, True):
            with self.assertRaises(ValueError): build_adapter(768, rank)

    def test_state_only_checkpoint_roundtrip(self):
        import torch
        a = build_adapter(16, 4)
        with torch.no_grad(): a.up.weight.fill_(.01)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'adapter.pt'
            torch.save({'state_dict': a.state_dict(), 'rank': 4}, path)
            checkpoint = torch.load(path, map_location='cpu', weights_only=True)
            b = build_adapter(16, checkpoint['rank']); b.load_state_dict(checkpoint['state_dict'], strict=True)
            x = torch.randn(1, 5, 16)
            self.assertTrue(torch.equal(a(x), b(x)))

    def test_saved_adapter_rejects_wrong_hash_and_base_identity(self):
        import hashlib
        import torch
        from neosignis.training.adapter import load_trained_adapter
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'adapter.pt'
            torch.save({'schema_version': 'neosignis.asl-encoder-adapter.v1', 'rank': 4, 'hidden_size': 16,
                        'base_checkpoint_sha256': 'a' * 64, 'adapter_state_dict': build_adapter(16, 4).state_dict()}, path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            adapter, _ = load_trained_adapter(path, expected_sha256=digest, expected_base_sha256='a' * 64)
            self.assertEqual(sum(p.numel() for p in adapter.parameters()), 148)
            with self.assertRaisesRegex(ValueError, 'hash'):
                load_trained_adapter(path, expected_sha256='b' * 64, expected_base_sha256='a' * 64)
            with self.assertRaisesRegex(ValueError, 'base'):
                load_trained_adapter(path, expected_sha256=digest, expected_base_sha256='b' * 64)

    def test_selection_is_reproducible_excludes_short_and_overbudget_without_truncation(self):
        from types import SimpleNamespace
        class Data:
            manifest = {'publisher_split': 'train'}
            def __len__(self): return 5
            def __getitem__(self, i):
                return SimpleNamespace(id=str(i), features=[0] * [9, 30, 40, 200, 35][i], text=['a', 'b', 'c', 'd', 'long'][i])
        tokenizer = SimpleNamespace(encode=lambda text, truncation: [1] * (70 if text == 'long' else 8))
        selected, excluded = select_training(Data(), tokenizer, count=2)
        self.assertEqual(set(selected), {1, 2})
        self.assertEqual(selected, select_training(Data(), tokenizer, count=2)[0])
        self.assertEqual({r['reason'] for r in excluded}, {'short_clip_pending_review', 'frame_budget', 'target_budget'})
        Data.manifest = {'publisher_split': 'val'}
        with self.assertRaisesRegex(ValueError, 'training split'): select_training(Data(), tokenizer, count=2)

    def test_run_output_cannot_overwrite_prepared_inputs(self):
        import importlib.util
        script = Path(__file__).resolve().parents[1] / 'scripts/data/train_asl_adapter.py'
        spec = importlib.util.spec_from_file_location('train_asl_adapter_cli_test', script)
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as tmp:
            with patch('sys.argv', ['train', '--data-root', tmp, '--output', tmp]), patch('sys.stderr', io.StringIO()):
                with self.assertRaises(SystemExit): cli.main()
            self.assertEqual(list(Path(tmp).iterdir()), [])


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('transformers'), 'Optional real tiny decoder tests')
class DecoderTests(unittest.TestCase):
    def setUp(self):
        import torch
        from transformers import MT5Config, MT5ForConditionalGeneration
        torch.set_num_threads(2); torch.manual_seed(23)
        self.base = MT5ForConditionalGeneration(MT5Config(vocab_size=32, d_model=16, d_ff=32, d_kv=8,
                                                         num_layers=1, num_decoder_layers=1, num_heads=2,
                                                         dropout_rate=0, decoder_start_token_id=0, eos_token_id=1, pad_token_id=0))
        freeze_base(self.base)
        self.adapter = build_adapter(16, 4)
        self.encoded, self.mask = torch.randn(1, 6, 16), torch.tensor([[1, 1, 1, 1, 0, 0]])
        self.labels = torch.tensor([[2, 3, 4, 1]])

    def test_actual_decoder_gradients_update_adapter_while_base_stays_identical(self):
        import torch
        from neosignis.training.adapter import decoder_loss, fit_step
        original = {k: v.clone() for k, v in self.base.state_dict().items()}
        before = float(decoder_loss(self.base, self.adapter, self.encoded, self.mask, self.labels).detach())
        optimizer = torch.optim.AdamW(self.adapter.parameters(), lr=.01)
        for _ in range(12):
            loss, norm = fit_step(self.base, self.adapter, optimizer, self.encoded, self.mask, self.labels)
            self.assertGreaterEqual(norm, 0); self.assertGreaterEqual(loss, 0)
        after = float(decoder_loss(self.base, self.adapter, self.encoded, self.mask, self.labels).detach())
        self.assertLess(after, before)
        self.assertTrue(all(torch.equal(v, original[k]) for k, v in self.base.state_dict().items()))
        self.assertTrue(all(p.grad is None for p in self.base.parameters()))

    def test_optimizer_cannot_include_base_and_base_cannot_be_unfrozen(self):
        import torch
        from neosignis.training.adapter import fit_step
        wrong = torch.optim.AdamW(list(self.adapter.parameters()) + list(self.base.parameters()))
        with self.assertRaisesRegex(ValueError, 'only adapter'):
            fit_step(self.base, self.adapter, wrong, self.encoded, self.mask, self.labels)
        next(self.base.parameters()).requires_grad_(True)
        with self.assertRaisesRegex(ValueError, 'frozen'):
            fit_step(self.base, self.adapter, torch.optim.AdamW(self.adapter.parameters()), self.encoded, self.mask, self.labels)

    def test_evaluation_has_no_update_and_reports_token_weighted_loss(self):
        import torch
        from neosignis.training.adapter import evaluate_loss
        before = {k: v.clone() for k, v in self.adapter.state_dict().items()}
        samples = [{'id': 'validation-fixture', 'encoded': self.encoded, 'mask': self.mask, 'labels': self.labels}]
        result = evaluate_loss(self.base, self.adapter, samples)
        self.assertEqual(result['target_tokens'], 4)
        self.assertTrue(all(torch.equal(v, before[k]) for k, v in self.adapter.state_dict().items()))
        self.assertTrue(all(p.grad is None for p in self.adapter.parameters()))

    def test_full_targets_are_kept_or_rejected_not_truncated(self):
        import torch
        from neosignis.training.adapter import prepare_labels
        class Tokenizer:
            def __call__(self, texts, *, padding, truncation, return_tensors):
                if truncation: raise AssertionError('No truncation')
                return {'input_ids': torch.ones(1, 87, dtype=torch.long), 'attention_mask': torch.ones(1, 87, dtype=torch.long)}
        self.assertEqual(prepare_labels(Tokenizer(), ['long target'], max_tokens=128).shape[1], 87)
        with self.assertRaisesRegex(ValueError, 'budget'): prepare_labels(Tokenizer(), ['long target'], max_tokens=50)

    def test_generation_does_not_receive_reference_labels(self):
        from types import SimpleNamespace
        import torch
        from neosignis.training.adapter import generate_text
        received = {}
        def generate(**kwargs):
            received.update(kwargs)
            return torch.tensor([[0, 2, 1]])
        tokenizer = SimpleNamespace(eos_token_id=1, decode=lambda ids, skip_special_tokens: 'fixture prediction')
        result = generate_text(SimpleNamespace(generate=generate), tokenizer, self.adapter,
                               {'encoded': self.encoded, 'mask': self.mask, 'text': 'private reference'})
        self.assertNotIn('labels', received)
        self.assertNotIn('input_ids', received)
        self.assertFalse(result['output_limit_reached'])


if __name__ == '__main__': unittest.main()
