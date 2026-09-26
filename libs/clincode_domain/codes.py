"""Pure ICD-10-CM / CPT structural validation and coding rules.

No database, no HTTP. Everything is a function of its arguments, so the entire
coding rule surface is testable before a single model is trained.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ICD10CM_PATTERN = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?$")
CPT_PATTERN = re.compile(r"^[0-9]{5}([0-9]{4}[A-Z])?$")

LATERALITY_CHAPTERS = ("S", "T", "M", "H")
UNSPECIFIED_MARKERS = ("9", ".9", ".90", ".99")


class InvalidCode(ValueError):
    pass


@dataclass(frozen=True)
class Code:
    code: str
    description: str
    is_billable: bool = True
    is_manifestation: bool = False
    requires_laterality: bool = False


@dataclass(frozen=True)
class Finding:
    rule_code: str
    severity: str  # info | warning | error
    message: str
    involved: tuple[str, ...] = ()


def normalise(code: str) -> str:
    """Upper-case, strip spaces; ICD dot is significant and is preserved."""
    cleaned = code.strip().upper().replace(" ", "")

    if not cleaned:
        raise InvalidCode("empty code")

    return cleaned


def is_valid_icd10cm(code: str) -> bool:
    try:
        return bool(ICD10CM_PATTERN.match(normalise(code)))
    except InvalidCode:
        return False


def is_valid_cpt(code: str) -> bool:
    try:
        return bool(CPT_PATTERN.match(normalise(code)))
    except InvalidCode:
        return False


def chapter_letter(code: str) -> str:
    return normalise(code)[0]


def is_unspecified(code: str) -> bool:
    c = normalise(code)
    return c.endswith(UNSPECIFIED_MARKERS) if "." in c else c.endswith("9")


@dataclass
class RuleSet:
    max_unspecified_ratio: float = 0.25
    excludes1: set[tuple[str, str]] = field(default_factory=set)
    manifestation_codes: set[str] = field(default_factory=set)

    def validate_set(
        self,
        codes: list[Code],
        principal: str | None,
    ) -> list[Finding]:
        findings: list[Finding] = []

        values = [normalise(c.code) for c in codes]

        for v in values:
            if not is_valid_icd10cm(v):
                findings.append(
                    Finding(
                        "STRUCT_INVALID",
                        "error",
                        f"{v} is not a well-formed ICD-10-CM code",
                        (v,),
                    )
                )

        for c in codes:
            if not c.is_billable:
                findings.append(
                    Finding(
                        "NOT_BILLABLE",
                        "error",
                        f"{c.code} is a header code and cannot be reported",
                        (c.code,),
                    )
                )

        for a in values:
            for b in values:
                if a < b and frozenset((a, b)) in self.excludes1:
                    findings.append(
                        Finding(
                            "EXCLUDES1",
                            "error",
                            f"{a} and {b} can never be reported together",
                            (a, b),
                        )
                    )

        if principal is None:
            findings.append(
                Finding(
                    "NO_PRINCIPAL",
                    "error",
                    "Encounter has no principal diagnosis",
                )
            )
        else:
            p = normalise(principal)

            if p not in values:
                findings.append(
                    Finding(
                        "PRINCIPAL_NOT_IN_SET",
                        "error",
                        f"Principal {p} is not among the reported codes",
                        (p,),
                    )
                )

            elif p in self.manifestation_codes:
                findings.append(
                    Finding(
                        "MANIFESTATION_PRINCIPAL",
                        "error",
                        f"{p} is a manifestation code and cannot be principal",
                        (p,),
                    )
                )

        for c in codes:
            if c.requires_laterality and is_unspecified(c.code):
                findings.append(
                    Finding(
                        "LATERALITY_UNSPECIFIED",
                        "warning",
                        f"{c.code} requires laterality but is unspecified",
                        (c.code,),
                    )
                )

        if values:
            ratio = sum(is_unspecified(v) for v in values) / len(values)

            if ratio > self.max_unspecified_ratio:
                findings.append(
                    Finding(
                        "UNSPECIFIED_RATIO",
                        "warning",
                        f"{ratio:.0%} of codes are unspecified",
                    )
                )

        return findings


def sequence(codes: list[Code], principal: str) -> list[str]:
    """Principal first, then remaining codes in stable input order."""
    p = normalise(principal)

    rest = [
        normalise(c.code)
        for c in codes
        if normalise(c.code) != p
    ]

    return [p] + rest