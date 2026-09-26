#!/usr/bin/env python
"""Stage ClinCode reference terminology and note corpora into data/raw/."""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
TERM = RAW / "terminology"
NOTES = RAW / "notes"

# Public terminology releases (no credentials required)
PUBLIC = {
    "terminology/hcpcs_2026.zip":
        "https://www.cms.gov/files/zip/hcpcs-quarterly-update.zip",
}

# Credentialed corpora — list only; the user must accept the DUA themselves
CREDENTIALED = [
    (
        "MIMIC-IV-Note",
        "https://physionet.org/content/mimic-iv-note/",
        "place discharge.csv.gz under data/raw/notes/mimic/",
    ),
    (
        "n2c2 2018 ADE",
        "https://n2c2.dbmi.hms.harvard.edu/",
        "place the annotated .ann/.txt pairs under data/raw/notes/n2c2/",
    ),
]


def fetch(rel: str, url: str) -> None:
    target = RAW / rel
    if target.exists():
        print(f"[skip] {rel}")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"[get] {rel}")
    urlretrieve(url, target)

    if target.suffix == ".zip":
        with zipfile.ZipFile(target) as zf:
            zf.extractall(target.parent)


def main() -> int:
    for d in (TERM, NOTES):
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()

    for rel, url in PUBLIC.items():
        try:
            fetch(rel, url)
        except Exception as exc:
            print(f"[warn] {rel} failed: {exc}")

    print()
    print("Credentialed corpora must be downloaded manually after signing the DUA:")
    for name, url, hint in CREDENTIALED:
        print(f"  - {name}: {url}")
        print(f"    {hint}")

    print()
    print("PHI reminder: data/raw/ is git-ignored. Never commit note text.")
    print("Next: python scripts/load_terminology.py && dvc add data/raw/")
    return 0


if __name__ == "__main__":
    sys.exit(main())