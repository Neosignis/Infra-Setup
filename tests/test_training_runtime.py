import importlib.util
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Optional PyTorch runtime tests')
class RuntimeTests(unittest.TestCase):
    def test_baseline_output_cannot_replace_source_input(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/data/run_asl_baseline.py'
        spec = importlib.util.spec_from_file_location('baseline_cli', path)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with patch('sys.argv', ['baseline', '--archive', 'source.zip', '--inventory', 'inventory.json',
                                '--references', 'refs.csv', '--output', 'source.zip']):
            with self.assertRaisesRegex(ValueError, 'overwrite a source'):
                cli.main()

    def make_model(self):
        import torch

        class Tokenizer:
            def __init__(self):
                self.last_texts = None

            def __call__(self, texts, *, padding, truncation, return_tensors):
                if truncation:
                    raise AssertionError('Targets must stay whole')
                self.last_texts = texts
                length = max(len(text.split()) + 1 for text in texts)
                ids = torch.ones((len(texts), length), dtype=torch.long)
                mask = torch.zeros_like(ids)
                for i, text in enumerate(texts):
                    mask[i, :len(text.split()) + 1] = 1
                class Batch(dict):
                    def to(self, device):
                        return {key: value.to(device) for key, value in self.items()}
                return Batch(input_ids=ids, attention_mask=mask)

        class Decoder(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.encoder = SimpleNamespace(embed_tokens=torch.nn.Embedding(4, 8))
                self.last_labels = None

            def forward(self, *, inputs_embeds, attention_mask, labels):
                self.last_labels = labels
                return SimpleNamespace(loss=inputs_embeds.square().mean())

        model = SimpleNamespace(
            modes=['body', 'left', 'right', 'face_all'],
            proj_linear={name: torch.nn.Linear(3, 4) for name in ['body', 'left', 'right', 'face_all']},
            gcn_modules={name: torch.nn.Identity() for name in ['body', 'left', 'right', 'face_all']},
            fusion_gcn_modules={name: torch.nn.Identity() for name in ['body', 'left', 'right', 'face_all']},
            pose_proj=torch.nn.Linear(16, 8), part_para=torch.nn.Parameter(torch.zeros(16)),
            mt5_model=Decoder(), mt5_tokenizer=Tokenizer())
        source = {'name_batch': ['a', 'b'], 'attention_mask': torch.tensor([[1] * 7, [1, 1, 1, 0, 0, 0, 0]])}
        for name, joints in [('body', 9), ('left', 21), ('right', 21), ('face_all', 18)]:
            source[name] = torch.ones((2, 7, joints, 3))
        return model, source

    def test_pose_prefix_mask_and_temporal_dimensions_match(self):
        from neosignis.training.unisign_runtime import pose_embeddings
        model, source = self.make_model()
        result = pose_embeddings(model, source)
        self.assertEqual(result['inputs_embeds'].shape[:2], result['attention_mask'].shape)
        self.assertEqual(result['inputs_embeds'].shape[0], 2)
        self.assertEqual(result['inputs_embeds'].shape[2], 8)
        self.assertEqual(result['attention_mask'][1, -7:].tolist(), source['attention_mask'][1].tolist())

    def test_full_targets_over_fifty_tokens_and_backward(self):
        from neosignis.training.unisign_runtime import translation_loss
        model, source = self.make_model()
        long = ' '.join(['word'] * 85)
        loss = translation_loss(model, source, [long, 'Short sentence.'])
        self.assertEqual(model.mt5_model.last_labels.shape, (2, 86))
        self.assertEqual(model.mt5_model.last_labels[1, -1], -100)
        loss.backward()
        self.assertIsNotNone(model.pose_proj.weight.grad)

    def test_explicit_target_budget_rejects_without_truncation(self):
        from neosignis.training.unisign_runtime import translation_loss
        model, source = self.make_model()
        with self.assertRaisesRegex(ValueError, 'budget'):
            translation_loss(model, source, ['word ' * 85, 'Other'], max_target_tokens=50)


if __name__ == '__main__':
    unittest.main()
