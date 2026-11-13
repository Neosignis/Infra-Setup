# ASL engine options and selection gate

Research checked against primary project/vendor sources on 13 November 2026. No candidate has been downloaded, benchmarked, licensed for Neosignis or integrated. The architecture keeps model and renderer replaceable because selection must follow data rights and independent evaluation.

| Path | Concrete starting point | What it can establish | Unresolved before adoption |
|---|---|---|---|
| Own bounded temporal baseline | PyTorch temporal model on consented phrase recordings, served behind `EngineProvider` | an owned narrow-domain engine and controlled signer-independent evaluation | enough diverse licensed recordings, negative examples, training and review capacity |
| Reuse pose recognition research | AI4Bharat OpenHands, which documents isolated-sign networks and WLASL checkpoints | a research baseline for isolated ASL recognition; not full-sentence translation | download availability, dependency/runtime compatibility, exact feature map, separate data/weight rights, local performance |
| Licensed commercial engine | Sign-Speak's documented ASL recognition and avatar API, if access/terms fit | a candidate external baseline or provider for measured comparison | trial access, contract, price, data retention, transfer/processing terms, independent quality and renderer rights |
| Train broader ASL translation | rights-cleared continuous ASL data and a separately evaluated temporal translation model | a future continuous-interpretation track | no commercially cleared continuous dataset or checkpoint was supplied; larger training/evaluation effort |

OpenHands publishes its library under Apache 2.0 and tells users to check dataset licenses separately. Its model documentation lists isolated-sign architectures and downloadable checkpoints. The library license must not be treated as permission for every dataset or checkpoint. [OpenHands maintainer README](https://github.com/AI4Bharat/OpenHands/blob/main/README.md), [model documentation](https://openhands.ai4bharat.org/en/latest/instructions/models.html).

Sign-Speak's vendor documentation describes video ASL recognition through REST/WebSocket interfaces and avatar offerings. Those descriptions establish an API candidate, not independently verified Neosignis quality. The current foundation accepts landmarks, so a video-based commercial adapter would need a separately versioned, consented RGB transport; feeding landmarks into that endpoint is not a compatible shortcut. [Vendor recognition specification](https://app.theneo.io/sign-speak/sign-speak-api/api-specifications/asl-production), [vendor API overview](https://app.theneo.io/sign-speak/sign-speak-api).

ASL Citizen is an isolated-sign dataset under Microsoft research terms. Its published license restricts use to non-commercial, non-revenue-generating research, and the project directs commercial-use inquiries to the maintainer. It must not be silently added to a commercial training path. [Microsoft dataset license](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/), [project and commercial-use note](https://www.microsoft.com/en-us/research/project/asl-citizen/).

How2Sign also has non-commercial terms, as documented in [the engine plan](engine.md). Other corpora/checkpoints need their own review; this shortlist does not clear them.

The proposed first implementation remains a bounded owned/appropriately licensed ASL model. Use a commercially licensed provider only if explicitly selected after access, privacy, costs and quality are measured. A phrase-classification demo is an intermediate engine milestone; it must not be marketed as unrestricted ASL interpretation.

## Selection checklist for the ML lead

Record exact repository/checkpoint version and digest; permitted code/weights/data/derivative uses; supported language/domain; input schema and preprocessing; tested hardware and memory; signer-independent semantic results and abstention; calibration; loading/serving cost; response-sign comprehension; and a rollback version with valid rights. Compare candidates on the same consented holdout. Select based on that report, then freeze the provider image and artifact manifest.
