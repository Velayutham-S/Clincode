# ADR 0002: Terminology as Data Rather Than Hardcoded Logic

- **Status:** Accepted (2026-09-12)
- **Deciders:** ClinCode core team
- **Milestone:** M1 (foundation)

## Context

ICD-10-CM is a large, official, versioned vocabulary: tens of thousands of codes
with descriptions, a hierarchy (chapter / block / category / subcategory),
billable (leaf) status, inclusion and exclusion notes, Excludes1 / Excludes2
relationships, and annual releases published by CMS/CDC. ClinCode's deterministic
coding rules — specificity, laterality, acuity, and especially Excludes1
validation — depend directly on this structured metadata.

Embedding codes or per-code rules directly in application logic would be
unmaintainable at this scale, would break with every annual release, would be
difficult to audit, and would scatter authoritative coding knowledge across the
codebase where it cannot be versioned or validated as a unit. It would also
conflict with the platform's core principle of **retrieval over unsupported
generation**.

## Decision

ICD-10-CM **codes, descriptions, hierarchy relationships, billable status,
inclusion/exclusion notes, and release metadata are stored as versioned data**,
not hardcoded in application logic.

1. Terminology is loaded from an **official CMS ICD-10-CM release** through a
   documented ETL step (implemented in a later M1 task).
2. Structured/relational data lives in **PostgreSQL**; vector representations for
   retrieval live in **Qdrant**.
3. A **single fixed release version** is used initially, and that version is
   recorded in both **configuration** and **database metadata** so every
   suggestion can be traced to the exact terminology release that produced it.
4. Application and pipeline code **reads terminology from these stores**. It does
   not embed code lists or per-code branching. Deterministic rules operate
   generically over the data (for example, Excludes1 checks query stored
   relationships rather than hardcoded code pairs).

## Consequences

**Positive**

- Annual updates become a data operation: load a new release and bump the version
  rather than editing code.
- Provenance and auditability: each suggestion can cite the terminology release
  it came from.
- Rules are testable against real data and remain in one authoritative place.
- Directly supports retrieval-not-generation and reproducibility.

**Negative / costs**

- Requires an ETL pipeline, a schema, and storage rather than a simple constant.
- Requires data-quality validation of the imported release.
- Requires disciplined release-version metadata management.
- Slightly more infrastructure than hardcoding a small list would need.

## Alternatives Considered

1. **Hardcode codes and rules in application code.** Rejected: unmaintainable at
   ICD-10-CM scale, not auditable, and breaks on every annual release.
2. **Call an external coding API at runtime.** Rejected for now: adds an external
   dependency and cost, raises data-egress/PHI concerns, and reduces control and
   reproducibility. May be revisited later.
3. **Keep only a flat CSV in the repository.** Rejected: loses the hierarchy and
   Excludes1 structure the rules require, adds a large file to Git, and offers no
   query capability. Raw source data is kept out of Git and loaded into the data
   stores instead.
4. **Support multiple annual releases from the start.** Deferred: unnecessary
   complexity for M1. We start with one fixed version and design the metadata so
   multi-release support can be added later without rework.
