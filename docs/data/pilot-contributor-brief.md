# Neosignis ASL collection pilot: draft contributor brief

Prepared 15 November 2026 for introductions and scoping. **This is not a consent agreement, employment offer or instruction to begin recording.** No budget, payment rate or contributor engagement has been agreed.

## Purpose

We are developing a two-way communication system: ASL signing to English text/speech, and English text/speech to understandable ASL. We are recruiting potential fluent Deaf ASL contributors and language reviewers to help define the scope and assess data quality. The existing camera app is an internal collection utility, not an ASL interpreter.

## People needed first

- A fluent Deaf ASL language lead to define prompts, natural variants and annotation rules.
- An independent fluent Deaf ASL reviewer to assess meaning, grammar and disagreements.
- An initial 3–5 adult contributors for a small collection-process pilot; later expansion across signers and conditions will need a separately costed plan.

Being fluent in a different signed language does not automatically qualify someone to provide ASL ground truth. We will plan a separate NSL collection/review track with relevant local expertise.

## Initial discussion

Please discuss ASL fluency, regional signing background, recording access/comfort, availability and proposed rates. Ask only for information relevant to the work. A reviewer may contribute recordings, but final evaluation should not rely exclusively on people who created or annotated training examples.

The team will define and agree compensation for preparation, recording, reviewing and reasonable rework before work starts. Do not promise payment per accepted clip without clearly explaining acceptance criteria and how contributor time/rework is compensated.

## Pilot proposal

After scope, permissions and compensation are agreed, target 100–200 accepted utterances across the initial contributors. Include everyday full utterances, important confusing meanings, questions/negation and selected unsupported/no-signing examples. Some examples can test capture mechanics; only linguistically reviewed signing can become model references.

Prompts describe intended meaning and context. Contributors should express them naturally in ASL, not translate English one word at a time. A different valid expression is not automatically an error. Review the actual recorded meaning rather than treating a prompt as proof of what was signed.

Controlled capture proposal: steady camera/stand, approximately 1080p/30 fps, face/upper body/both hands visible and adequate lighting. Preserve original orientation. Agree individual clip length from the prompt; the current camera utility has a ten-second cap and is not suitable for longer dialogue collection without changes. Do not cut a complete utterance to fit a tool limit. No microphone is required for the initial signer recordings.

## Permissions to settle separately

The final participant documents must state purposes, duration, recipients/access, storage, permitted derivatives, compensation and withdrawal processes. Distinguish:

- Recording and internal quality evaluation.
- Training/fine-tuning and the use/distribution of resulting models.
- Retaining and processing motion/keypoint data.
- Playing recorded signing back to users or distributing footage.
- Training/generating an identifiable digital likeness and synthetic output.

The initial recording pilot does not silently authorise the last two purposes. A realistic-signer contributor engagement, usage compensation/royalties and style-learning programme require their own clear agreement. Do not claim that every model can be technically unlearned on request; agree what withdrawal will mean for data, access and affected model versions.

## Handling recordings

Use pseudonymous signer codes in filenames, annotations and training manifests. Keep the identity/permission mapping separate and restricted. The team must provide the approved private upload/storage location before distributed collection. Do not send contributor media to public GitHub/Hugging Face repositories, social media or public issue attachments.

Every clip should have an opaque ID, signer/session ID, prompt/context, reviewed English references, technical metadata, permission-reference IDs, review status, version/checksum and dataset split. Test signers and their sessions must stay out of training. Give contributors an agreed contact route for questions, access and withdrawal requests.

## Questions for the introductory call

1. Which ASL varieties and communication settings do you use regularly?
2. Are you interested in recording, linguistic review, or both?
3. What availability, preparation needs and rates would you propose?
4. Which data/likeness uses would you consider or decline?
5. What would make recording/review accessible and comfortable for you?
6. Who else could independently review comprehension and naturalness?

## What counts as a successful pilot

All recordings have the agreed permissions and handling; actual signing and English references are checked; reviewer disagreements are recorded/resolved; original files are decodable and complete; checksums and provenance match; no test signer leaks into training. A pilot can succeed as a data process while exposing that a model is not ready. It must not be represented as proof of continuous translation quality.
