"""T2 (★가장 중요) — 필수 필드 미충족 candidate가 REFUTED로 승격되지 않음 (PRD N1).

사람 검수가 설계상 없으므로 이 테스트가 유일한 정확성 보증이다.
required_match_fields는 DB_SCHEMA.md 형식: {"scope":true,"metric":false,...} —
게이트는 applicability_check의 "<field>_match"를 본다 (§3 assemble_verdict).
"""
from counter.gate import assemble_verdict_code, passes_refuted_gate

# SUPERLATIVE_FIRST 시드 값: scope + timeframe 필수, 나머지 무관
REQUIRED = {"scope": True, "metric": False, "timeframe": True,
            "target_entity": False, "geography": False}

# RANKING 시드 값: metric + timeframe + geography 필수
REQUIRED_RANKING = {"scope": False, "metric": True, "timeframe": True,
                    "target_entity": False, "geography": True}


def _check(**overrides):
    base = {"scope_match": True, "metric_match": True, "timeframe_match": True,
            "target_entity_match": False, "geography_match": True,
            "is_syndicated_copy": False, "insufficient_access": False}
    base.update(overrides)
    return base


def test_all_required_true_passes():
    assert passes_refuted_gate(_check(), REQUIRED)


def test_any_required_false_fails():
    for field in ("scope_match", "timeframe_match"):
        assert not passes_refuted_gate(_check(**{field: False}), REQUIRED), field


def test_ranking_requires_geography():
    # "다른 회사도 1위 광고" 류 — 지표·기간은 맞아도 시장 정의(geography)가 다르면 안 깨짐
    assert not passes_refuted_gate(_check(geography_match=False), REQUIRED_RANKING)
    assert passes_refuted_gate(_check(scope_match=False), REQUIRED_RANKING)  # scope 무관


def test_not_required_field_ignored():
    # metric/target_entity는 SUPERLATIVE_FIRST에서 required=False — 값과 무관
    assert passes_refuted_gate(_check(metric_match=False, target_entity_match=False), REQUIRED)


def test_missing_field_fails_closed():
    assert not passes_refuted_gate({}, REQUIRED)


def test_insufficient_access_blocks_gate():
    assert not passes_refuted_gate(_check(insufficient_access=True), REQUIRED)


def test_syndicated_copy_blocks_gate():
    assert not passes_refuted_gate(_check(is_syndicated_copy=True), REQUIRED)


def test_assemble_refuted_only_with_passing_candidate():
    passing = {"applicability_check": _check(), "url": "https://a"}
    failing = {"applicability_check": _check(timeframe_match=False), "url": "https://b"}
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
