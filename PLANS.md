# Structurizr-First Implementation Plan

## Objective
Establish a reliable workflow to partner with an LM for Domain-Driven Design (DDD) and generate C4 Level 1 and Level 2 diagrams (System Context and Container) with Structurizr DSL as the single source of truth, exporting Mermaid as a downstream artifact.

## Success Criteria
- DDD artifacts are authored before architecture DSL.
- `architecture/workspace.dsl` is the canonical architecture definition.
- Structurizr CLI validation and inspection pass with no `error` violations.
- Mermaid output is generated from DSL (not manually authored as primary source).
- Diagram updates are reproducible from committed source files.

## Scope
- In scope:
  - DDD discovery artifacts (ubiquitous language, bounded contexts, context map, event flow notes).
  - Structurizr DSL model and views for:
    - System Context
    - Container
  - CLI validation, inspection, and Mermaid export workflow.
  - LM prompt contracts for repeatable collaboration.
- Out of scope:
  - C4 Component/Code views.
  - Deployment views.
  - Manual Mermaid-first authoring as primary architecture source.

## Proposed Artifact Structure
- `domain/ubiquitous-language.md`
- `domain/bounded-contexts.md`
- `domain/context-map.md`
- `domain/event-storming.md`
- `architecture/workspace.dsl`
- `architecture/mermaid/` (generated outputs)
- `prompts/ddd-to-c4.md`

## Implementation Phases

### Phase 1: Domain Baseline (DDD Inputs)
1. Create initial DDD artifacts under `domain/`:
   - Ubiquitous language glossary.
   - Bounded contexts and ownership.
   - Context map with integrations and translation points.
   - Event-storming summary for key business flows.
2. Define naming conventions:
   - Consistent context names.
   - Stable element naming for systems/containers.
3. Review and approve domain artifacts before modeling.

Exit criteria:
- All four domain documents exist.
- Team agrees on bounded context boundaries and core terminology.

### Phase 2: LM Prompt Contract
1. Create `prompts/ddd-to-c4.md` with strict instructions:
   - Input sources: only `domain/*.md`.
   - Output target: `architecture/workspace.dsl`.
   - Allowed views: System Context and Container only.
   - No invented systems/containers not grounded in domain files.
2. Require LM to emit:
   - Assumptions list.
   - Open questions list.
   - Proposed DSL changes.

Exit criteria:
- Prompt is reusable and explicit about constraints.
- LM output format is deterministic.

### Phase 3: Structurizr DSL Authoring
1. Create `architecture/workspace.dsl`:
   - Define people, software systems, containers, and relationships.
   - Add `systemContext` and `container` views for the primary system.
2. Keep identifiers stable to reduce churn in exported artifacts.
3. Apply minimal style configuration only if needed for readability.

Exit criteria:
- DSL parses and captures approved domain scope.
- Both required view types are present.

### Phase 4: Validation and Quality Gates
1. Run validation:
   - `./structurizr.sh validate -workspace architecture/workspace.dsl`
2. Run inspection:
   - `./structurizr.sh inspect -workspace architecture/workspace.dsl -severity error,warning`
3. Resolve all `error` findings.
4. Track unresolved warnings with rationale in PR notes or commit message.

Exit criteria:
- Validation succeeds.
- No inspection errors remain.

### Phase 5: Mermaid Export Pipeline
1. Export Mermaid diagrams:
   - `./structurizr.sh export -workspace architecture/workspace.dsl -format mermaid -output architecture/mermaid`
2. Treat `architecture/mermaid/` as generated artifacts.
3. Regenerate Mermaid outputs after every approved DSL change.

Exit criteria:
- Mermaid files are present and correspond to current DSL.
- Export process is repeatable without manual edits.

### Phase 6: Iteration and Change Management
1. Proposed change flow:
   - Update `domain/*.md` if business semantics changed.
   - Update `architecture/workspace.dsl`.
   - Re-run validate/inspect/export.
2. Keep Mermaid diffs reviewable:
   - Prefer stable names and relationships.
   - Avoid unnecessary reordering in DSL.
3. Require review sign-off on:
   - Domain boundary changes.
   - New containers.
   - External system dependency additions.

Exit criteria:
- Architecture evolves through source artifacts with traceable rationale.
- LM-assisted updates remain constrained and auditable.

## Definition of Done
- Required directories/files exist (or are intentionally deferred with notes).
- `workspace.dsl` is validated and inspected.
- Mermaid export is generated from DSL.
- Team can execute the workflow end-to-end with documented commands.

## Operational Notes
- Structurizr DSL remains the source of truth.
- Mermaid C4 syntax can be used for rendering/export consumption, but not as the primary authored model.
- If domain ambiguity is detected, resolve it in `domain/*.md` before accepting DSL edits.
