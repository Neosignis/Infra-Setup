# First ASL recognition/translation model

**Implementation update:** the [independent pose adapter, checkpoint validator and Mac compute check](data/pose-adapter-and-local-training.md) are implemented. Upstream source is now pinned to `eed438bcb49e30405cd6ccdfcccca330c134e830`; no explicit repository code licence was found. Actual extractor/checkpoint integration remains pending. The requirements below retain the initial decision context.

18 November 2026. **Select Uni-Sign's How2Sign pose-only SLT checkpoint as the first research baseline. No production model is approved or installed.** Selection is based on task fit and published assets, not a local accuracy comparison.

We need continuous signing translated into English sentences, including movement and facial information. A word classifier alone does not meet this requirement. The author's repository publishes an ASL checkpoint and pose extraction path; its pose-first approach fits our intended separation between visual extraction and translation. Reduced input size compared with full video is an engineering rationale, not a measured speed or quality claim. See the [official repository](https://github.com/ZechengLi19/Uni-Sign) and [input documentation](https://github.com/ZechengLi19/Uni-Sign/blob/main/docs/DATASET.md).

| Candidate | Decision for this step |
|---|---|
| Uni-Sign How2Sign pose-only SLT | First research baseline: ASL sentence translation and published task-specific weights. Requires new pose adapter. |
| SpaMo | Keep as RGB/motion research comparator if pose loses essential information. No local speed/quality comparison performed. [Author paper](https://aclanthology.org/2025.naacl-long.197/) |
| SSVP-SLT | Continuous ASL research comparator; additional video pipeline. Its repository also carries noncommercial terms. [Author repository](https://github.com/facebookresearch/ssvp_slt) |
| OpenHands/WLASL isolated-sign checkpoints | Useful word-recognition diagnostic, not our sentence-translation engine. [Maintainer documentation](https://github.com/AI4Bharat/OpenHands) |
| Whisper | Audio transcription; does not recognize signed video. [OpenAI model documentation](https://developers.openai.com/api/docs/models/whisper-1) |

## Exact asset and unresolved requirements

The [selection record](../ml/recognition-selection.json) pins `ZechengLi19/Uni-Sign`, revision `64a2e24003b6e6bdbafca4f24c5f387921cdc6f0`, file `how2sign_pose_only_slt.pth`. Publisher size is 1,186,925,007 bytes; SHA256 is `1bfd5f3312f04e4736f0a52f4ef9535916e6de9676a2a0d00c708748683fb00d`. These are publisher metadata, not a verified local download. [Publisher checkpoint record](https://huggingface.co/ZechengLi19/Uni-Sign/commit/64a2e24003b6e6bdbafca4f24c5f387921cdc6f0)

1. The model card marks weights **CC BY-NC 4.0**. Neither these weights nor How2Sign's public terms establish commercial permission. Review code, weights, extractor, decoder and training-data terms separately. Code revision/license review remains incomplete; no upstream implementation has been imported. [Model card](https://huggingface.co/ZechengLi19/Uni-Sign)
2. Extract the expected RTMPose whole-body 133 points and confidence, then verify body/hand/face selection and normalization against the frozen implementation. Our 553-point `landmarks.v1` request cannot simply be relabelled as that layout. The neutral loader exposes feature/missing-observation arrays; the checkpoint-specific adapter is still pending.
3. Freeze extractor/checkpoint/decoder revisions and hashes; install in an isolated ML environment. The upstream demo uses CUDA. Mac CPU/MPS compatibility and required GPU memory are not established here. No AWS instance or paid endpoint has been started.
4. Replace upstream random maximum-length frame subsampling with an explicitly tested full-utterance input path. Its supplied video demo does not establish incremental live interpretation. [Author dataset code](https://github.com/ZechengLi19/Uni-Sign/blob/main/datasets.py), [demo](https://github.com/ZechengLi19/Uni-Sign/blob/main/demo/online_inference.py)
5. Measure translation correctness with fluent Deaf ASL review on separate signers, abstention and semantic errors; report automated translation scores as supporting metrics. Measure end-to-end P50/P95 latency on real phone/desktop sessions before declaring this our MVP model. Current validation clips support development, not training or an independent final holdout.

This research choice can change after measurement. The commercial path is cleared weights/data or an independently implemented model trained on cleared recordings. Text-to-sign remains a separate component.
