#!/usr/bin/env python
"""Seed ClinCode terminology subset and de-identified demo encounters."""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row


DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'clincode')} "
    f"user={os.getenv('DB_USER', 'clincode')} "
    f"password={os.getenv('DB_PASS', 'clincode_dev_2026')}"
)

CODE_SET = "ICD10CM-FY2026"
CPT_SET = "CPT-2026"

ICD_CODES = [
    (
        "E11.9",
        "Type 2 diabetes mellitus without complications",
        "Endocrine",
        True,
        False,
        False,
    ),
    (
        "E11.22",
        "Type 2 diabetes mellitus with diabetic chronic kidney disease",
        "Endocrine",
        True,
        False,
        False,
    ),
    (
        "I10",
        "Essential (primary) hypertension",
        "Circulatory",
        True,
        False,
        False,
    ),
    (
        "I50.32",
        "Chronic diastolic (congestive) heart failure",
        "Circulatory",
        True,
        False,
        False,
    ),
    (
        "J18.9",
        "Pneumonia, unspecified organism",
        "Respiratory",
        True,
        False,
        False,
    ),
    (
        "J44.1",
        "COPD with (acute) exacerbation",
        "Respiratory",
        True,
        False,
        False,
    ),
    (
        "N18.30",
        "Chronic kidney disease, stage 3 unspecified",
        "Genitourinary",
        True,
        False,
        False,
    ),
    (
        "S72.001A",
        "Fracture of unspecified part of neck of right femur, initial encounter",
        "Injury",
        True,
        False,
        True,
    ),
    (
        "S72.002A",
        "Fracture of unspecified part of neck of left femur, initial encounter",
        "Injury",
        True,
        False,
        True,
    ),
    (
        "S72.009A",
        "Fracture of unspecified part of neck of unspecified femur, initial encounter",
        "Injury",
        True,
        False,
        True,
    ),
    (
        "A41.9",
        "Sepsis, unspecified organism",
        "Infectious",
        True,
        False,
        False,
    ),
    (
        "R65.21",
        "Severe sepsis with septic shock",
        "Symptoms",
        True,
        True,
        False,
    ),
]

CPT_CODES = [
    ("99223", "Initial hospital care, high complexity", "E/M"),
    ("99233", "Subsequent hospital care, high complexity", "E/M"),
    ("27130", "Total hip arthroplasty", "Surgery"),
    ("71046", "Radiologic examination, chest, 2 views", "Radiology"),
    ("80053", "Comprehensive metabolic panel", "Pathology"),
    ("93306", "Echocardiography, transthoracic, complete", "Medicine"),
]

RELATIONS = [
    (CODE_SET, "E11.9", "E11.22", "excludes1"),
    (CODE_SET, "A41.9", "R65.21", "use_additional"),
    (CODE_SET, "N18.30", "E11.22", "code_first"),
]

NOTE_TEMPLATE = (
    "CHIEF COMPLAINT\n"
    "Shortness of breath for three days.\n\n"
    "HISTORY OF PRESENT ILLNESS\n"
    "The patient is a [age] year old with a known history of "
    "type 2 diabetes mellitus and essential hypertension who presented "
    "with progressive dyspnea. No chest pain was reported.\n\n"
    "PAST MEDICAL HISTORY\n"
    "Type 2 diabetes mellitus. Hypertension. Chronic kidney disease "
    "stage 3.\n\n"
    "HOSPITAL COURSE\n"
    "Treated for community acquired pneumonia with intravenous "
    "antibiotics. Renal function remained stable.\n\n"
    "DISCHARGE DIAGNOSIS\n"
    "1. Pneumonia, unspecified organism\n"
    "2. Type 2 diabetes mellitus without complications\n"
    "3. Essential hypertension\n"
)


def seed_terminology(cur) -> None:
    cur.execute(
        """
        INSERT INTO code_sets
            (code_set_id, system, release_year, effective_from)
        VALUES
            (%s, 'ICD10CM', 2026, '2025-10-01')
        ON CONFLICT DO NOTHING
        """,
        (CODE_SET,),
    )

    cur.execute(
        """
        INSERT INTO code_sets
            (code_set_id, system, release_year, effective_from)
        VALUES
            (%s, 'CPT', 2026, '2026-01-01')
        ON CONFLICT DO NOTHING
        """,
        (CPT_SET,),
    )

    cur.executemany(
        """
        INSERT INTO codes
            (
                code_set_id,
                code,
                short_desc,
                long_desc,
                chapter,
                is_billable,
                is_manifestation,
                requires_laterality
            )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
        """,
        [
            (CODE_SET, c, d, d, ch, b, m, lat)
            for c, d, ch, b, m, lat in ICD_CODES
        ],
    )

    cur.executemany(
        """
        INSERT INTO codes
            (code_set_id, code, short_desc, long_desc, chapter)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
        """,
        [
            (CPT_SET, c, d[:120], d, ch)
            for c, d, ch in CPT_CODES
        ],
    )

    cur.executemany(
        """
        INSERT INTO code_relations
            (code_set_id, code, related_code, relation_type)
        VALUES (%s,%s,%s,%s)
        """,
        RELATIONS,
    )


def seed_encounters(cur, n: int = 25) -> None:
    now = datetime.now(timezone.utc)

    for i in range(n):
        cur.execute(
            """
            INSERT INTO patients
                (deid_ref, birth_year, sex)
            VALUES (%s,%s,%s)
            RETURNING patient_id
            """,
            (
                f"DEID-{i:05d}",
                random.randint(1940, 1995),
                random.choice(["M", "F"]),
            ),
        )

        patient_id = cur.fetchone()["patient_id"]

        admitted = now - timedelta(days=random.randint(5, 200))

        cur.execute(
            """
            INSERT INTO encounters
                (
                    patient_id,
                    external_ref,
                    encounter_type,
                    admitted_at,
                    discharged_at,
                    discharge_disposition,
                    payer
                )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING encounter_id
            """,
            (
                patient_id,
                f"ENC-{i:06d}",
                random.choice(["inpatient", "observation"]),
                admitted,
                admitted + timedelta(days=random.randint(2, 9)),
                "home",
                random.choice(["Medicare", "Commercial", "Self-pay"]),
            ),
        )

        encounter_id = cur.fetchone()["encounter_id"]

        body = NOTE_TEMPLATE.format(
            age=random.randint(45, 84)
        )

        cur.execute(
            """
            INSERT INTO clinical_notes
                (encounter_id, note_type, authored_at, body)
            VALUES (%s,%s,%s,%s)
            RETURNING note_id
            """,
            (
                encounter_id,
                "discharge_summary",
                admitted + timedelta(days=3),
                body,
            ),
        )

        note_id = cur.fetchone()["note_id"]

        for name in (
            "chief_complaint",
            "hpi",
            "past_medical",
            "hospital_course",
            "discharge_dx",
        ):
            marker = {
                "chief_complaint": "CHIEF COMPLAINT",
                "hpi": "HISTORY OF PRESENT ILLNESS",
                "past_medical": "PAST MEDICAL HISTORY",
                "hospital_course": "HOSPITAL COURSE",
                "discharge_dx": "DISCHARGE DIAGNOSIS",
            }[name]

            start = body.find(marker)

            if start < 0:
                continue

            end = body.find("\n\n", start)

            if end < 0:
                end = len(body)

            cur.execute(
                """
                INSERT INTO note_sections
                    (note_id, section_name, start_offset, end_offset)
                VALUES (%s,%s,%s,%s)
                """,
                (
                    note_id,
                    name,
                    start,
                    end if end > start else len(body),
                ),
            )


def main() -> None:
    random.seed(20260911)

    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM code_sets")

            if cur.fetchone()["c"] > 0:
                print("already seeded; run 'make reset' first to reseed")
                return

            seed_terminology(cur)
            seed_encounters(cur)

            cur.execute(
                """
                INSERT INTO audit_log
                    (actor, action, resource_type, resource_id, detail)
                VALUES
                    (
                        'seed_script',
                        'SEED',
                        'database',
                        'clincode',
                        '{"milestone":"M1"}'
                    )
                """
            )

        conn.commit()

    print(
        "seeded: 2 code sets, 18 codes, 3 relations, "
        "25 encounters with sectioned notes"
    )


if __name__ == "__main__":
    main()