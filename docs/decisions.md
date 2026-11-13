# Architecture decisions

These decisions describe the proposed baseline dated 13 November 2026. The user has authorized architecture creation; recording them does not imply team approval or model validation.

| ADR | Decision | Reason | Reconsider when |
|---|---|---|---|
| 001 | Engine before meeting integrations | user's stated immediate priority; integrations cannot solve recognition | G1/G2 passed and engine contract is stable |
| 002 | ASL first, independent NSL | confirmed user preference; languages need their own evidence | NSL data/review capability exists |
| 003 | One monorepo, modular API, separate ML process | clear ownership, fewer deployable parts; ML lifecycle differs | workloads require independent worker scaling |
| 004 | CPU Fargate, GPU ECS EC2 | use managed CPU tasks while retaining GPU access | measured managed-inference economics win |
| 005 | No EKS/Kafka/vector database initially | no demonstrated requirement; operational burden would precede engine evidence | concrete scheduling, replay or semantic retrieval need |
| 006 | Recorded phrase output before realistic avatar | bounded response test can validate meaning with available consented footage | validated realistic motion/identity assets exist |
| 007 | No automatic recording or training | privacy and contributor rights require explicit purposes | separately consented research capture is implemented |
| 008 | Explicit unavailable/abstain states | API health does not establish translation ability | never remove; expand tested capabilities only |
| 009 | Distinct env/account/state | limits blast radius and production access | organization account strategy changes |
| 010 | No automatic Terraform apply from PR | cloud changes need a reviewed concrete plan and environment policy | protected deployment workflow is implemented |
| 011 | Semantic representation includes non-manual/spatial information | word/gloss sequencing loses meaning | evaluate richer representation, never discard needed cues |
