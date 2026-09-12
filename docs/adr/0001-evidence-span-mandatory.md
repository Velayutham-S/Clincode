# ADR 0001: Evidence Spans Are Mandatory

- **Status:** Accepted (2026-09-12)
- **Deciders:** ClinCode core team
- **Milestone:** M1 (foundation)

## Context

ClinCode suggests ICD-10-CM codes for clinical notes, but the final coding
decision always belongs to a human coder. For the platform to be trustworthy and
useful, a coder must be able to verify each suggestion quickly, and a compliance
reviewer must be able to audit why a code was proposed.

Keyword-based and black-box computer-assisted coding tools typically return a
bare code with no traceable justification. This makes verification as slow as
coding from scratch and hides the exact errors ClinCode must avoid: coding a
negated condition, a family-history mention, a historical/resolved condition, or
an uncertain finding as if it were a confirmed active diagnosis. The pipeline
also transforms text through many stages, so the link between a suggestion and
the original text is easily lost if offsets are not preserved deliberately.

## Decision

Every code suggestion **must** carry a structured evidence reference back to the
source note:

1. The exact character span (start/end offsets) into the stored, de-identified
   note, plus the containing sentence and section.
2. Character offsets are preserved end to end across every pipeline stage.
   Stages that transform text must preserve or explicitly remap offsets, and the
   stored note is immutable and versioned so offsets remain valid.
3. A suggestion without a valid evidence span is not a valid final suggestion
   and must not be surfaced as trustworthy.
4. Any LLM-generated explanation must be grounded in the referenced span
   (verified by a groundedness check) or it is suppressed. The underlying
   deterministic suggestion may still stand, because the code comes from
   retrieval and rules, not from the LLM.

## Consequences

**Positive**

- Coders verify suggestions in seconds by jumping to the supporting sentence.
- Suggestions are auditable and defensible for compliance review.
- Assertion status stays bound to a specific span, improving safety.
- Grounding checks for generated text become possible and enforceable.

**Negative / costs**

- Every pipeline stage must carry and validate offsets, adding invariants that
  must be maintained.
- De-identification must preserve or remap offsets rather than freely rewriting
  text.
- Span-preservation tests become load-bearing.
- Requires immutable, versioned storage of the note so offsets do not drift.

## Alternatives Considered

1. **Code-only suggestions (no evidence).** Rejected: not verifiable, not
   auditable, and unsafe given assertion-related failure modes.
2. **Whole-note or section-level attribution only.** Rejected as the primary
   mechanism: too coarse for fast verification and for tying assertion status to
   a specific mention. Section context is still included alongside exact spans.
3. **Post-hoc LLM rationales without offset grounding.** Rejected: can
   hallucinate justifications and cannot be reliably audited.
4. **Keyword highlighting without structured offsets.** Rejected: brittle,
   breaks under normalization/synonyms, and unreliable for audit.
