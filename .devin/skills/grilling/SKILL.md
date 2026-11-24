---
name: grilling
description: "Clarify scope, constraints, and acceptance criteria before implementing a new BioETL request. Once the task is agreed and needs a staged implementation plan, use py-plan-bot."
---

# Clarify a BioETL task

The repository's `../../../AGENTS.md` sets the trigger and confirmation requirement.
Apply this procedure before editing files, changing data or settings, or
taking external action. The task class determines when to consult
`../../../docs/00-project/RULES.md`,
`../../../docs/01-requirements/REQUIREMENTS.md`, and accepted ADRs in
`../../../docs/02-architecture/decisions`.

1. Read the relevant repository material and available evidence. Resolve factual
   questions from those sources and carry forward decisions already made.
2. Identify open decisions about the goal, deliverable, scope, constraints, and
   acceptance criteria. Start with decisions whose prerequisites are settled.
3. Ask the smallest useful set of questions in each round. Recommend an answer
   for each and explain its material tradeoff. Wait for answers before asking
   dependent questions.
4. When the scope is clear, summarize the shared understanding and check for
   explicit approval covering it. If approval is still needed, request
   confirmation before implementing. If the request is already complete, skip
   further clarification questions.
5. On follow-up, revisit only decisions affected by a scope change. Follow the
   root rule for an explicit request to proceed without questions.
