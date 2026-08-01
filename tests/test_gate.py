"""T2 (★가장 중요) — 필수 필드 미충족 candidate가 REFUTED로 승격되지 않음 (PRD N1).

사람 검수가 설계상 없으므로 이 테스트가 유일한 정확성 보증이다.
"""
from counter.gate import assemble_verdict_code, passes_refuted_gate

REQUIRED = {"scope_match": True, "metric_match": True,
            "timeframe_match": True, "target_match": False}


def _check(**overrides):
    base = {"scope_match": True, "metric_match": True, "timeframe_match": True,
            "target_match": False, "is_syndicated_copy": False, "insufficient_access": False}
    base.update(overrides)
    return base


def test_all_required_true_passes():
    assert passes_refuted_gate(_check(), REQUIRED)


def test_any_required_false_fails():
    for field in ("scope_match", "metric_match", "timeframe_match"):
        assert not passes_refuted_gate(_check(**{field: False}), REQUIRED), field


def test_not_required_field_ignored():
    # target_match는 required=False이므로 값과 무관하게 통과에 영향 없음
    assert passes_refuted_gate(_check(target_match=False), REQUIRED)
    assert passes_refuted_gate(_check(target_match=True), REQUIRED)


def test_missing_field_fails_closed():
    assert not passes_refuted_gate({}, REQUIRED)


def test_insufficient_access_blocks_gate():
    assert not passes_refuted_gate(_check(insufficient_access=True), REQUIRED)


def test_syndicated_copy_blocks_gate():
    assert not passes_refuted_gate(_check(is_syndicated_copy=True), REQUIRED)


def test_assemble_refuted_only_with_passing_candidate():
    passing = {"applicability_check": _check(), "url": "https://a"}
    failing = {"applicability_check": _check(metric_match=False), "url": "https://b"}
    code, winning = assemble_verdict_code([failing, passing], REQUIRED, True)
    assert code == "REFUTED" and winning is passing

    code, winning = assemble_verdict_code([failing], REQUIRED, True)
    assert code == "NOT_REFUTED" and winning is None


def test_no_successful_search_is_substantiation_not_found():
    code, _ = assemble_verdict_code([], REQUIRED, any_search_succeeded=False)
    assert code == "PUBLIC_SUBSTANTIATION_NOT_FOUND"


def test_zero_results_is_not_refuted_not_error():
    # 검색 결과 0건은 정상 경로 (ARCHITECTURE §7)
    code, _ = assemble_verdict_code([], REQUIRED, any_search_succeeded=True)
    assert code == "NOT_REFUTED"
