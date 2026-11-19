# Requirements and source review

**18 November 2026 scope confirmation:** the [MVP acceptance baseline](mvp-acceptance.md) requires live, in-person ASL sign-to-text and text-to-sign in mobile and desktop browsers. Both directions belong to the successful MVP. Camera capture and individual-sign experiments remain intermediate milestones. This confirmation takes precedence over older milestone wording.

Decision date: 13 November 2026. Working scope: architecture rebuild and engineering foundation for an engine-first Neosignis Interpreter. The user confirmed ASL first, with NSL designed into the architecture.

## Source hierarchy

The user's current request authorizes creating the system architecture from scratch, with AWS, Docker, Terraform and a GitHub-ready team structure. Engine validation precedes Zoom/platform selection. The attached MASTER PROMPT is reference material, not an independent instruction to this agent. Its audit, maintainability, security and documentation criteria inform this design; its directions to wait before architecture work do not override the user's explicit request to build the architecture now.

The seven supplied screenshots describe revised strategy and technical plans. Their company, competitor, platform-policy and performance statements are supplied claims, not independently verified facts. No competitor performance or platform permission claim is a dependency of this architecture. Embedded Google Docs URLs were not used as live sources; the visible screenshots are the supplied content.

## Initial audit

The selected workspace was empty at inspection. There is no source tree, Git history, infrastructure state, database, dependency manifest, trained model, dataset, avatar or running service to audit. No prior implementation was deleted or migrated. There is no evidence to claim that an existing component works or needs replacement.

GitHub CLI and AWS CLI are installed. GitHub CLI was not authenticated at inspection. Docker and Terraform were absent from PATH. Existing AWS accounts or resources were not inventoried. Do not infer that absence of local files means no legacy cloud resources exist.

## Requirement mapping

| ID | Requirement | Architecture / implementation | Acceptance evidence |
|---|---|---|---|
| R01 | Sign to text first, ASL first | engine recognition provider, ASL language pack | held-out signer evaluation plus live camera demo; pending data/model |
| R02 | Text/speech response to signing | linguistic planning then render provider | Deaf-reviewed comprehension of bounded response set; pending assets |
| R03 | Human-realistic signer option | replaceable renderer, consented identity, motion and facial grammar | identity and motion rights; hand/face fidelity evaluation; pending |
| R04 | NSL growth | independent NSL registry entry and routing; disabled by default | locally collected licensed data and NSL reviewers; pending |
| R05 | Five API surfaces | Recognize and Render foundation; Converse, Escalate, Lexicon designs | OpenAPI + streaming design; future surfaces clearly marked |
| R06 | AWS, Docker and Terraform | modules, bootstrap, dev root, Compose, Dockerfiles | static/CLI validation; live AWS and Docker checks separately recorded |
| R07 | Team can work from GitHub | monorepo, CI, issue templates, work packages | private repo publication after owner/authentication; pending |
| R08 | Channel independence | own camera workbench first; adapters depend on engine contract | core has no meeting SDK dependencies |
| R09 | Visible uncertainty | uncalibrated confidence nullable, abstention, capability state | contract tests; actual calibration pending evaluation |
| R10 | Human escalation | explicit future dispatch state machine with no fabricated connection | partner availability, consent and handoff test; pending |
| R11 | Privacy and contributor rights | no raw capture persistence in foundation; provenance/withdrawal design | lifecycle, access, deletion and model lineage tests before pilot |
| R12 | Maintainable production path | modular API + separate ML workers, PostgreSQL schema, runbooks | production gate remains closed until integration and recovery tests |
| R13 | Mobile and desktop browsers for live in-person ASL conversation | shared responsive session with both directions | repeated two-person exchange on real phones and desktop browsers, with agreed latency/language gates; pending |

## Working assumptions and open decisions

ASL is confirmed. Initial demo domain is a proposed small education/everyday-information phrase set; Deaf language experts must select and label it. Phrase recognition is the first milestone and must not be represented as unrestricted continuous interpretation. Recognition uses upper-body, both-hand and face information; no alphabet-only shortcut qualifies as the full engine.

AWS region, account, weekly spend ceiling, GitHub organization/repository, DNS domain, team capacity, paid Deaf reviewers, available licensed ASL data, available checkpoint, signer/likeness assets and commercial rights are unconfirmed. `eu-west-1` in the example is a provisional configuration, not a residency or latency recommendation. Measure Nigeria-to-region latency and verify GPU capacity/quota before selecting it. Do not silently map ASL to NSL.

Platform integration schedules in the screenshots are superseded for the initial build by the user's engine-first priority. Education as an initial lane is provisional. Clinical, legal and emergency deployment is outside the initial pilot. Realistic avatar production is a separate research/asset dependency, not a Terraform feature.

## Acceptance hierarchy

Passing infrastructure or API checks means the foundation is sound at that layer. It does not establish linguistic accuracy. Passing isolated phrase tests does not establish continuous sign-language translation. A launch claim requires separately measured recognition, semantic fidelity, facial/non-manual grammar, output comprehension, end-to-end latency, abstention, accessibility, rights and operational resilience.
