---
name: "PRP: Non-Technical AI Coding Workflow Optimization (DoD Gate + Context Packs)"
description: |
  Make Archon dramatically easier for non-technical users who rely on AI agents for coding.

  This PRP focuses on preventing overconfident incomplete implementations by introducing:
  - A Work Order Contract (requirements + acceptance criteria + constraints)
  - A Definition-of-Done (DoD) Gate that requires evidence before claiming completion
  - Structured clarification and feedback loops (forms, not paragraphs)
  - Reusable Context Packs to stop repetitive requirement explanations

  IMPORTANT: This PRP is planning-only. Do not start implementation yet.
---

## Goal

**Feature Goal**: Reduce user frustration and rework by ensuring agents (1) ask the right questions early, (2) do not claim completion without evidence, and (3) retain and reuse context so users don’t repeat themselves.

**Deliverable**: A new “Non-Technical Mode” workflow inside Agent Work Orders that:
1) guides the user through a simple work-order wizard,
2) forces an evidence-backed completion report,
3) supports structured feedback to generate follow-up work orders.

**Success Definition** (measurable):
- 50% reduction in “follow-up work orders created because original was incomplete” (baseline → after rollout)
- 30% reduction in median time-to-acceptable-result for non-technical users
- ≥80% of completed work orders include an evidence bundle and an acceptance-criteria checklist

## User Persona

**Target User**: Non-technical “vibe coder” who depends entirely on AI agents for coding.

**Use Case**: “I want feature X. I don’t know how to specify it technically, but I can recognize correct/incorrect outcomes.”

**User Journey**:
1. User clicks “New Work Order (Guided)”
2. User describes goal in plain English + selects options (speed vs safety, breaking changes allowed, etc.)
3. System asks a small number of clarifying questions (structured form)
4. Agent runs workflow and streams progress (logs already supported via SSE)
5. Agent produces a completion report that maps acceptance criteria → evidence
6. User marks criteria as Met/Not Met/Unsure
7. If any Not Met/Unsure → one click creates follow-up work order with carried-over context

**Pain Points Addressed**:
- Agents declaring “done” without actually finishing
- Users having to explain requirements repeatedly
- Users not knowing what to say when something is missing
- Unclear visibility into what was actually changed

## Why

### Current Archon Benefits (what’s already strong)

These existing strengths make this workflow improvement feasible:
- Agent Work Orders already exist as a dedicated workflow system with persistent state:
  - `archon_agent_work_orders` and `archon_agent_work_order_steps` tables (see migration/agent_work_orders_state.sql)
- Real-time progress observability exists:
  - SSE log stream architecture is already implemented and documented (see PRPs/ai_docs/AGENT_WORK_ORDERS_SSE_AND_ZUSTAND.md)
- Clear architectural boundaries:
  - UI vertical slices + backend service layer + optional microservices (see PRPs/ai_docs/ARCHITECTURE.md)

### Where Archon Needs Improvement (for non-technical AI collaboration)

- Requirements are often implicit and not captured in a machine-checkable format.
- Agents can complete partial work and still “sound confident” because there is no enforced DoD gate.
- Feedback loops require the user to write long explanations; this is hard and leads to miscommunication.
- Context reuse is weak: prior decisions and constraints are not packaged and re-applied reliably.

## What (User-visible behavior + technical requirements)

### Non-Technical Mode: Key Behaviors

1) **Guided Work Order Creation**
- The user fills a short wizard: Goal → Preferences → Clarifying Questions → Review.

2) **Work Order Contract is the Source of Truth**
- Every work order has a persisted contract:
  - Requirements list
  - Acceptance criteria checklist
  - Constraints / non-goals
  - Clarifying questions + answers

3) **DoD Gate for Completion**
- The agent cannot mark a work order completed unless:
  - All acceptance criteria are addressed (Met/Not Met/Unsure)
  - An evidence bundle is attached
  - Any blockers are listed explicitly

4) **Structured Feedback Loop (No More Paragraphs)**
- If user says “not correct”, UI asks:
  - What category? (Missing feature / wrong behavior / didn’t run / UI mismatch / performance)
  - Which acceptance criteria failed?
  - Optional free-text note (1–2 sentences)
- One click creates a follow-up work order using the same context.

### Success Criteria

- [ ] A work order can be created in “Guided” mode without typing technical details.
- [ ] A work order cannot be marked completed without a DoD report.
- [ ] The completion report shows acceptance criteria → evidence mapping.
- [ ] User can mark acceptance criteria Met/Not Met/Unsure.
- [ ] A follow-up work order can be created from unmet criteria with one click.
- [ ] Context Packs can be reused across work orders.

## All Needed Context

### Documentation & References

```yaml
- docfile: PRPs/ai_docs/ARCHITECTURE.md
  why: Confirms vertical slice structure, service layers, and microservice boundaries.

- docfile: PRPs/ai_docs/AGENT_WORK_ORDERS_SSE_AND_ZUSTAND.md
  why: Defines SSE patterns, state management standards, and how real-time logs are represented.

- file: migration/agent_work_orders_state.sql
  why: Shows available tables and JSONB metadata fields we can extend for contracts/evidence.
  gotcha: Keep frequently queried fields as columns; store flexible data as JSONB.

- file: python/src/server/api_routes/agent_work_orders_proxy.py
  why: Confirms main API already proxies agent-work-orders microservice.
```

### Current Codebase tree

(Already present in repo; no changes required for this PRP.)

### Desired Codebase tree (high-level)

```text
archon-ui-main/src/features/agent-work-orders/
  components/
    NonTechnicalWizard/
      Wizard.tsx
      steps/
        GoalStep.tsx
        PreferencesStep.tsx
        ClarificationsStep.tsx
        ReviewStep.tsx
    WorkOrderCompletionReport/
      CompletionReport.tsx
      AcceptanceChecklist.tsx
      EvidencePanel.tsx
      FeedbackPanel.tsx
  services/
    agentWorkOrdersService.ts (extend existing)
  hooks/
    useAgentWorkOrderQueries.ts (extend existing)

python/src/agent_work_orders/
  services/
    contract_service.py
    evidence_service.py
  api_routes/
    contracts_api.py
    evidence_api.py
  workflows/
    (extend workflow to enforce DoD gate)

migration/
  agent_work_orders_contracts.sql (new)
  agent_work_orders_context_packs.sql (new)
```

## Proposed Solution (Concepts)

### Concept A: Work Order Contract

**Definition**: A structured JSON object attached to each work order that includes requirements, acceptance criteria, constraints, and clarifications.

**Why it works**: It creates a stable “single source of truth” so the agent can’t drift, and the user can’t be forced to restate requirements.

**Data**:
- Minimal required fields:
  - `goal` (string)
  - `acceptance_criteria` (array of checklist items)
  - `constraints` (array)
  - `non_goals` (array)
  - `clarifying_questions` (array of {question, answer})

### Concept B: DoD Gate + Completion Report

**Definition**: A final mandatory step that produces:
- `acceptance_criteria_status` (Met/Not Met/Unsure)
- Evidence bundle
- A short “what changed” summary

**Evidence bundle examples**:
- Changed files list (paths)
- Commands attempted (tests/lint/build)
- Key logs (from SSE events)
- Any known limitations (“not run because …”)

### Concept C: Context Packs

**Definition**: Reusable collections of “what the agent should always know” for this user/project.

**Examples**:
- Pinned files
- Preferences: “Always ask before DB migrations”, “Prefer small diffs”, “Run tests if available”
- Decisions: “No backwards compatibility”, “Fix-forward”

### Concept D: Structured Feedback → Follow-up Work Orders

**Definition**: The UI converts user dissatisfaction into actionable structured input.

**Outcome**: Less repetition; follow-up tasks are automatically well-formed.

## Integration With Existing Archon Architecture

### Where this should live
- Primary UI surface: Agent Work Orders (because it already supports multi-step workflows and logs)
- Primary backend: Agent Work Orders microservice (python/src/agent_work_orders)
- Main API: keep using the existing proxy route (no need for UI to talk to a new port)

### MCP Server integration
- Optional but recommended:
  - Add MCP tools that can create/update work orders and append feedback.
  - This allows IDE-based agents to participate while still obeying the DoD Gate.

## Data Models and Structure (Planning)

### Option 1 (fastest): Store Contract + Evidence in JSONB `metadata`
- Put `contract` and `completion_report` inside `archon_agent_work_orders.metadata`.
- Pros: minimal DB change.
- Cons: harder to query/report at scale.

### Option 2 (recommended): New tables for Contracts and Context Packs

1) `archon_agent_work_order_contracts`
- `agent_work_order_id` (FK)
- `contract` (JSONB)
- `created_at`, `updated_at`

2) `archon_context_packs`
- `context_pack_id` (UUID)
- `name` (text)
- `scope` (text: user/project)
- `content` (JSONB)
- indexes for lookup by scope

## Implementation Blueprint (Phased)

### Phase 0: UX-only Prototype (no backend changes)
- Add a “Guided mode” wizard UI that outputs a JSON preview of the contract.
- Validate the wording and flow with non-technical users.

### Phase 1: Persist Work Order Contract
- On create/update, store contract with the work order (Option 1 or 2).
- Ensure the contract is visible in the UI and included in all agent prompts.

### Phase 2: Enforce DoD Gate
- Add a required “completion_report” step.
- Prevent status from transitioning to `completed` unless completion_report exists.

### Phase 3: Structured Feedback + Follow-up
- Add UI controls to mark criteria Met/Not Met/Unsure.
- Add a “Create Follow-up Work Order” button that seeds a new contract.

### Phase 4: Context Packs
- Add save/apply UI for context packs.
- Auto-attach relevant context packs to new work orders.

### Phase 5: Metrics + Continuous Improvement
- Track: number of follow-ups, time-to-acceptance, % completion with evidence.
- Use metrics to improve defaults (ask more questions, smaller steps).

## Validation Loop (Planning)

### Level 1: UX Validation (non-technical)
- Can a user create a work order without writing technical requirements?
- Can a user understand completion report without reading code?

### Level 2: System Validation
- Work order cannot become completed without DoD report.
- Follow-up work order carries over unmet criteria.

### Level 3: Regression Safety
- Existing agent work order flows still work when “Guided” mode is not used.

## Risks & Mitigations

- **Risk**: Too much ceremony slows down quick experiments.
  - Mitigation: “Guided mode” optional; provide templates and defaults.

- **Risk**: Agents still claim completion in logs.
  - Mitigation: only the system status matters; UI treats “completed” as gated by DoD.

- **Risk**: JSONB becomes unqueryable mess.
  - Mitigation: keep a stable contract schema + add dedicated tables if analytics needed.

## Open Questions (to answer before implementation)

1) Should “Non-Technical Mode” be a global toggle or per-work-order?
2) Do we want to require “tests run” evidence, or just allow “not run with reason”?
3) What are the top 5 clarification questions we can standardize as defaults?

<!-- EOF -->
