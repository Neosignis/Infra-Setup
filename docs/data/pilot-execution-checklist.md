# First dataset pilot: working checklist

18 November 2026. This follows the founder's five-step sequence and the [confirmed MVP](../mvp-acceptance.md). It is a collection-process pilot, not a claim of conversational accuracy.

| Step | Current state | Next evidence needed |
|---|---|---|
| 1. Freeze everyday meanings | Twelve draft meanings prepared; no fluent reviewer available yet | Reviewer identity, approved contexts/variants, confusing examples and a signed-off version |
| 2. Inspect a small permitted sample | Selected PopSign hello/validation archive downloaded: 157 MP4 files; size/structure/hashes checked; ten archive regression tests pass | Complete archive, recorded hash/size, safe file inventory, video inspection, label/participant compatibility |
| 3. Commission recordings | Not started; 3–5 contributors and 100–200 reviewed utterances remain the process-pilot target | Agreed contributors, compensation, purpose-specific permissions and linguistic review capacity |
| 4. Store approved data privately | Dataset Terraform prepared and mocked tests pass; no cloud deployment verified | Working local AWS login, reviewed live plan/apply, scoped upload access and synthetic upload/recovery test |
| 5. Train/evaluate a baseline | Not started; no model or approved corpus | Rights-cleared/versioned data, model choice, signer-disjoint splits and agreed evaluation thresholds |

## Meaning-set review

The [machine-readable draft](../../ml/data/everyday-meanings.draft.json) reuses the capture UI's E01–E12 IDs. English prompts describe an intended meaning; they are not instructions to sign English word by word. No ASL gloss or model-generated signing has been approved.

| ID | Draft meaning |
|---|---|
| E01 | Hello |
| E02 | Thank you |
| E03 | Please — context still needs definition |
| E04 | Yes |
| E05 | No |
| E06 | I need help |
| E07 | I understand |
| E08 | I do not understand |
| E09 | Please repeat that |
| E10 | Please sign more slowly |
| E11 | How are you? |
| E12 | I am fine |

Some seeds are standalone signs; the final MVP collection must also contain natural complete utterances. The reviewer can replace or combine seeds where a standalone English word is a poor prompt. Preserve the difference between a prompt and what the contributor actually signed. Record legitimate alternative expressions and context rather than automatically marking them wrong.

For each item, the reviewer supplies the actual ASL equivalent/context, acceptable variants, non-manual requirements and confusing/out-of-scope examples. Distinguish understanding from not understanding, yes from no, and statements from questions. The developer/founder's online checks do not become linguistic approval.

## Online references and the review boundary

[ASL University/Lifeprint](https://www.lifeprint.com/) and [HandSpeak](https://www.handspeak.com/) can support sign/context research. Their pages do not automatically grant training, playback or likeness rights. Do not copy dictionary clips into our corpus without the required permission.

ASL has grammar distinct from English and is expressed through hands and face; a word lookup cannot certify a complete utterance. See the [NIDCD ASL overview](https://www.nidcd.nih.gov/health/american-sign-language). Until fluent review is available, continue file acquisition, technical tests, pipeline experiments and review preparation, while retaining explicit unreviewed status. Do not claim that unsupported full-utterance translation is validated.

The [existing contributor brief](pilot-contributor-brief.md) can be used to scope a paid reviewer and recording engagement. No outreach or recording commission has been sent by this work.

## Sample scope and storage

The chosen initial source is **PopSign v1.0, game, validation, hello**, documented CC BY 4.0. Its archive is 925,061,120 bytes. This is one sign for technical inspection, not a multi-class training set or independent MVP test set. Its validation split is development material; final evaluation still needs independent signers.

Raw media and per-file inventories belong under ignored `data/local/`, not Git. The read-only inspector hashes and checks TAR structure without extraction. It does not decode video, judge ASL, establish model compatibility, approve training rights or verify signer splits. Use original source footage rather than altered website previews.

Only about 18 GiB was free locally at acquisition start. Full ASL Citizen alone is listed as 42.8 GB, and full How2Sign/PopSign releases are larger. No full-corpus download is scheduled. How2Sign, ASL Citizen and CLERC remain outside product training pending establishment of permitted use; source/licence review is not commercial clearance.

## Review checkmarks

- [ ] Meanings and full-utterance scope approved by a fluent Deaf ASL reviewer.
- [x] Selected original archive downloaded, inventoried and size/structure/hash checked.
- [ ] Video decoding, recording quality, label/signer compatibility and linguistic review completed.
- [ ] Actual signing and English meanings independently reviewed.
- [ ] Contributor compensation and each permitted purpose agreed.
- [ ] Source/licence, pseudonymous signer/session, checksums and review state recorded.
- [ ] Private storage, access and recovery verified before participant collection.
- [ ] Training/tuning/final-test people and recordings separated.
- [ ] Model evaluation measures meaning, uncertainty, unsupported inputs and latency on actual phone/web input.

Software unit tests verify mechanics. Separate ASL review and held-out real-signing evaluation determine whether the interpreter preserves meaning.

## Completed acquisition

The selected archive and per-file report are in ignored `data/local/popsign_v1_0/game/val/`. The [public acquisition summary](popsign-sample-acquisition-2026-11-18.json) records 925,061,120 bytes, 157 MP4s and the archive SHA256. A private original clip copy is available for playback, but programmatic decoding and linguistic review have not been performed. The Python suite passes 64 tests, including ten source-archive regressions. No AWS upload or training has run. The user subsequently provided the How2Sign frontal validation ZIP in Downloads: 1,739 MP4s passed structural/CRC/hash checks and match reference IDs, with two reference rows lacking video. Earlier automated download attempts had been quota-blocked. Other source videos remain unacquired. Storage and permitted-use prerequisites remain separate.

## Input-readiness update

A deterministic 32-clip How2Sign sample now fully decodes; this does not replace full-corpus checks or fluent ASL review. Mixed reported frame rates and 240 matched reference utterances longer than ten seconds expose concrete preprocessing/transport requirements. See [the readiness report and local commands](preprocessing-readiness.md). No model was trained, no final holdout was scored and no signing-output assets were approved.
