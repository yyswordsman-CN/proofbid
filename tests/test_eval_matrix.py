from collections import Counter

from proofbid.evals import EVAL_CASES


def test_eval_matrix_has_fifty_balanced_unique_cases() -> None:
    assert len(EVAL_CASES) == 50
    assert len({case.case_id for case in EVAL_CASES}) == 50
    assert Counter(case.category for case in EVAL_CASES) == {
        "structure": 10,
        "evidence_missing": 10,
        "product_pricing": 10,
        "security": 10,
        "failure_recovery": 10,
    }
