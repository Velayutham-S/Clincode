import pytest

from libs.clincode_domain.codes import (
    Code,
    InvalidCode,
    RuleSet,
    is_unspecified,
    is_valid_cpt,
    is_valid_icd10cm,
    normalise,
    sequence,
)


@pytest.mark.parametrize("code", ["E11.9", "I10", "S72.001A", "A41.9", "N18.30"])
def test_valid_icd_codes(code):
    assert is_valid_icd10cm(code)


@pytest.mark.parametrize("code", ["U07", "11.9", "E1", "E11.", "e11.9.2", ""])
def test_invalid_icd_codes(code):
    assert not is_valid_icd10cm(code)


def test_cpt_accepts_five_digits_and_category_two():
    assert is_valid_cpt("99223")
    assert is_valid_cpt("0001F")
    assert not is_valid_cpt("9922")


def test_normalise_rejects_blank():
    with pytest.raises(InvalidCode):
        normalise(" ")


def test_unspecified_detection():
    assert is_unspecified("J18.9")
    assert is_unspecified("I10") is False  # no dot, ends with 0
    assert not is_unspecified("E11.22")


def test_excludes1_pair_is_an_error():
    rs = RuleSet(
        excludes1={frozenset(("E11.9", "E11.22"))}
    )

    codes = [
        Code("E11.9", "T2DM"),
        Code("E11.22", "T2DM with CKD"),
    ]

    findings = rs.validate_set(
        codes,
        principal="E11.9",
    )

    assert any(
        f.rule_code == "EXCLUDES1" and f.severity == "error"
        for f in findings
    )


def test_missing_principal_is_an_error():
    findings = RuleSet().validate_set(
        [Code("I10", "HTN")],
        principal=None,
    )

    assert any(
        f.rule_code == "NO_PRINCIPAL"
        for f in findings
    )


def test_manifestation_cannot_be_principal():
    rs = RuleSet(
        manifestation_codes={"R65.21"}
    )

    codes = [
        Code("A41.9", "Sepsis"),
        Code(
            "R65.21",
            "Septic shock",
            is_manifestation=True,
        ),
    ]

    findings = rs.validate_set(
        codes,
        principal="R65.21",
    )

    assert any(
        f.rule_code == "MANIFESTATION_PRINCIPAL"
        for f in findings
    )


def test_laterality_warning_only_when_required():
    rs = RuleSet()

    needs = [
        Code(
            "S72.009A",
            "Femur fracture unspecified side",
            requires_laterality=True,
        )
    ]

    assert any(
        f.rule_code == "LATERALITY_UNSPECIFIED"
        for f in rs.validate_set(needs, "S72.009A")
    )

    fine = [
        Code(
            "S72.001A",
            "Right femur fracture",
            requires_laterality=True,
        )
    ]

    assert not any(
        f.rule_code == "LATERALITY_UNSPECIFIED"
        for f in rs.validate_set(fine, "S72.001A")
    )


def test_header_code_is_not_reportable():
    codes = [
        Code(
            "N18.30",
            "CKD stage 3",
            is_billable=False,
        )
    ]

    assert any(
        f.rule_code == "NOT_BILLABLE"
        for f in RuleSet().validate_set(codes, "N18.30")
    )


def test_sequence_puts_principal_first():
    codes = [
        Code("I10", "HTN"),
        Code("J18.9", "Pneumonia"),
        Code("E11.9", "T2DM"),
    ]

    assert sequence(codes, "J18.9") == [
        "J18.9",
        "I10",
        "E11.9",
    ]