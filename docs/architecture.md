# ClinCode — Architecture

## 1. Context

ClinCode handles two document classes:

- **Structured EHR exports** — already sectioned.
- **Scanned PDFs** — requiring OCR.

Both document classes converge on a single `clinical_notes` row with a stable character-offset space. Every downstream evidence span is expressed as an offset pair against the canonical note text.

M1 provisions storage and terminology. No model is trained during M1.

## 2. Component Responsibilities

| Component | Responsibility |
|---|---|
| `document-intake` | Receives a note or PDF, stores the original in MinIO, and registers the encounter. |
| `nlp-extraction` | Segments the note, runs clinical NER, and writes concept spans with offsets. |
| `code-suggester` | Maps extracted concepts to ICD-10-CM / CPT candidates with confidence scores. |
| `validation-agent` | Applies coding rules such as exclusions, laterality, and sequencing, and flags conflicts. |
| `coder-api` | FastAPI service serving the coder worklist and accept/reject actions. |

## 3. Data Flow

1. `document-intake` writes the original document to MinIO, normalizes the text, and stores the canonical note text so offsets remain stable.
2. `nlp-extraction` segments the note by section header, runs NER, and writes `concept_spans` with:
   - `start_offset`
   - `end_offset`
   - Negation flags
   - Historicity flags
3. `code-suggester` embeds each concept span, queries Qdrant against embedded code descriptions, and writes ranked `code_suggestions` linked to the span.
4. `validation-agent` applies the rule set and writes `validation_findings`.
5. `coder-api` exposes the worklist. Every accept/reject action is recorded in `coder_decisions`.

## 4. Non-Functional Targets

- Every suggested code must resolve to at least one evidence span; otherwise, it must not be shown.
- Note text is immutable once stored.
- Corrections create a new note version.
- No PHI is stored in logs, Git, or MLflow artifacts.
- Terminology is versioned.
- Each suggestion records the code-set release that produced it.