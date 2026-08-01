"""T2 (★가장 중요) — 필수 필드 미충족 candidate가 CONTRADICTED/CORROBORATED로
승격되지 않음 (PRD N1 확장, 3단계 판정).

사람 검수가 설계상 없으므로 이 테스트가 유일한 정확성 보증이다.
required_match_fields는 DB_SCHEMA.md 형식: {"scope":true,"metric":false,...} —
게이트는 applicability_check의 "<field>_match"를 본다 (§3 assemble_verdict).
"""
from counter.gate import assemble_verdict_code, passes_corroboration_gate, passes_refuted_gate

# SUPERLATIVE_FIRST 시드 값: scope + timeframe 필수, 나머지 무관
REQUIRED = {"scope": True, "metric": False, "timeframe": True,
            "target_entity": False, "geography": False}

# RANKING 시드 값: metric + timeframe + geography 필수
REQUIRED_RANKING = {"scope": False, "metric": True, "timeframe": True,
                    "target_entity": False, "geography": True}


def _check(**overrides):
    base = {"scope_match": True, "metric_match": True, "timeframe_match": True,
            "target_entity_match": False, "geography_match": True,
            "supports_claim": False,
            "is_syndicated_copy": False, "insufficient_access": False}
    base.update(overrides)
    return base


# ---- CONTRADICTED (반박) 게이트 ----

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


def test_supports_claim_excludes_from_contradiction_gate():
    # 방향이 뒷받침인 문서는 차원이 전부 맞아도 반박 후보가 아니다
    assert not passes_refuted_gate(_check(supports_claim=True), REQUIRED)


# ---- CORROBORATED (뒷받침) 게이트 — 반박 게이트와 동일한 차원 요건, 방향만 반대 ----

def test_corroboration_requires_supports_claim():
    assert not passes_corroboration_gate(_check(supports_claim=False), REQUIRED)
    assert passes_corroboration_gate(_check(supports_claim=True), REQUIRED)


def test_corroboration_same_dimension_rules_apply():
    assert not passes_corroboration_gate(
        _check(supports_claim=True, timeframe_match=False), REQUIRED)


def test_corroboration_blocks_syndicated_and_insufficient():
    assert not passes_corroboration_gate(
        _check(supports_claim=True, is_syndicated_copy=True), REQUIRED)
    assert not passes_corroboration_gate(
        _check(supports_claim=True, insufficient_access=True), REQUIRED)


# ---- assemble_verdict_code — 3단계 조립 ----

def test_assemble_contradicted_only_with_passing_candidate():
    passing = {"applicability_check": _check(), "url": "https://a"}
    failing = {"applicability_check": _check(timeframe_match=False), "url": "https://b"}
    code, winning = assemble_verdict_code([failing, passing], REQUIRED)
    assert code == "CONTRADICTED" and winning is passing

    code, winning = assemble_verdict_code([failing], REQUIRED)
    assert code == "UNVERIFIED" and winning is None


def test_assemble_corroborated_when_no_contradiction_but_support_found():
    supporting = {"applicability_check": _check(supports_claim=True), "url": "https://c"}
    code, winning = assemble_verdict_code([supporting], REQUIRED)
    assert code == "CORROBORATED" and winning is supporting


def test_contradiction_wins_over_corroboration():
    # 같은 배치에 반박 후보와 뒷받침 후보가 둘 다 있으면 반박이 우선한다
    contradicting = {"applicability_check": _check(), "url": "https://a"}
    supporting = {"applicability_check": _check(supports_claim=True), "url": "https://c"}
    code, winning = assemble_verdict_code([supporting, contradicting], REQUIRED)
    assert code == "CONTRADICTED" and winning is contradicting


def test_zero_results_is_unverified_not_error():
    # 검색 결과 0건은 정상 경로 (ARCHITECTURE §7)
    code, winning = assemble_verdict_code([], REQUIRED)
    assert code == "UNVERIFIED" and winning is None
