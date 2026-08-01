"""S6. VERDICT ASSEMBLY — 결정론적 3단계 판정 + 2단 가드레일.

▸ 왜 마지막: 판정은 검색 결과(근거)가 존재한 뒤에만 나온다 (PRD N3).
순서 (ARCHITECTURE §1 S6):
  ① 3단계 게이트 — LLM 선언이 아니라 코드 조건문 (PRD N1, counter/gate.py)
     CONTRADICTED(반박 근거) / CORROBORATED(뒷받침 근거) / UNVERIFIED(둘 다 없음)
  ② 가드레일 1단 — LLM(luna)으로 법적 결론 어휘 1차 차단
  ③ 가드레일 2단 — 최종 JSON 정규식 금지어 검사 → 걸리면 재생성 1회 (counter/guardrail.py).
     UNVERIFIED는 추가로 "긍정 결론 어휘" 정규식도 통과해야 한다 — 반증을
     못 찾은 것을 "진실일 가능성이 있다"로 오독하게 만드는 문구를 코드로 차단.
  ④ DB 기록 + 스트림 push
근거를 지어내지 않는다 (N6): evidence_link는 검색 결과에 실제 존재한 URL만.
DB의 chk_evidence_only_if_refuted 제약이 최후 방어선 (T9).
confidence_source: fresh_search | cached_reuse | delta_search (DB_SCHEMA.md verdict).
"""
from __future__ import annotations

from ..db import normalized_hash
from ..gate import NO_THIRD_PARTY_VERIFICATION_TYPES, assemble_verdict_code
from ..guardrail import SAFE_FALLBACK, contains_banned, contains_positive_conclusion, guard
from .. import prompts, schemas
from .s5_search import _safe_date


def assemble_from_cache(*, claim: dict, claim_id: str, canonical: dict,
                        oai, db, settings, emitter) -> dict:
    """캐시 히트 — 재검색 없이 canonical의 최신 verdict를 재사용 (지연 차이가 데모 포인트)."""
    cached = db.latest_verdict_for_canonical(canonical["canonical_id"])
    if cached is None:
        # canonical은 있는데 verdict가 없는 비정상 상태 — 방어적으로 UNVERIFIED 계약 문구
        cached = {"verdict_code": "UNVERIFIED", "evidence_link": None,
                  "evidence_date": None, "search_count": 0,
                  "reasoning": "축적된 판정 레코드를 찾지 못했습니다."}
    executed_queries = db.fetch_executed_queries(claim_id, canonical["canonical_id"])
    verdict_id = db.insert_verdict(
        claim_id=claim_id, canonical_id=canonical["canonical_id"],
        verdict_code=cached["verdict_code"], evidence_link=cached.get("evidence_link"),
        evidence_date=cached.get("evidence_date"),
        search_count=0,  # 이번 조회에서 실행한 검색은 0 — 재사용이 핵심
        confidence_source="cached_reuse",
        required_evidence_note=None, reasoning=cached.get("reasoning"),
    )
    db.update_claim_routing(claim_id, canonical_id=canonical["canonical_id"])
    emitter.emit("verdict.assembled", {
        "verdict_id": verdict_id, "claim_text": claim["claim_text"],
        "verdict_code": cached["verdict_code"], "evidence_link": cached.get("evidence_link"),
        "confidence_source": "cached_reuse", "reuse_count": canonical.get("reuse_count"),
        "executed_queries": executed_queries,
    }, provider="app")
    return {"verdict_id": verdict_id, "verdict_code": cached["verdict_code"]}


def assemble_from_search(*, claim: dict, claim_id: str, category_id: str,
                         cache_decision: str, canonical: dict | None,
                         search_outcome: dict, falsifier_spec: dict,
                         embedding: list[float] | None, oai, db, settings, emitter,
                         degraded_reason: str | None) -> dict:
    """풀/델타/재검증 검색 후 판정 조립 → canonical 축적 → 기록."""
    required = falsifier_spec["required_match_fields"]
    candidates = search_outcome["candidates"]
    executed_queries = search_outcome["executed_queries"]

    # ① 결정론적 3단계 게이트 (N1) — CONTRADICTED / CORROBORATED / UNVERIFIED
    verdict_code, winning = assemble_verdict_code(candidates, required)
    evidence_link = winning["url"] if winning else None
    evidence_date = _safe_date(winning["published_date"]) if winning else None

    evidence_note = degraded_reason
    if (verdict_code == "UNVERIFIED" and not winning
            and search_outcome["any_search_succeeded"]
            and claim["claim_type_code"] in NO_THIRD_PARTY_VERIFICATION_TYPES
            and not evidence_note):
        # 검색 자체는 정상 수행됐지만 claim_type이 구조적으로 제3자 검증
        # 불가능한 경우(gate.NO_THIRD_PARTY_VERIFICATION_TYPES) — S5 타임아웃/실패
        # 사유(degraded_reason)와는 다른 사유를 남긴다.
        evidence_note = ("이 주장은 비상장/사기업이 자체 발표한 정량 지표로, "
                         "법정 공시나 제3자 감사 대상이 아닙니다")

    reasoning = _make_explanation(
        claim=claim, verdict_code=verdict_code, winning=winning,
        executed_queries=executed_queries, oai=oai, settings=settings,
        emitter=emitter, degraded_reason=evidence_note,
    )

    # canonical 축적 — 다음 유사 질문의 캐시/델타 기반 (PRD §6-3)
    if canonical is not None:
        canonical_id = canonical["canonical_id"]
        db.mark_canonical_searched(canonical_id)  # last_searched_at 갱신 + 재검증 리셋
    else:
        canonical_id = db.create_canonical(
            representative_claim_id=claim_id,
            claim_type_code=claim["claim_type_code"],
            industry_category_id=category_id,
            claim_hash=normalized_hash(claim["normalized_text"]),
            embedding=embedding,
            similarity_threshold_used=settings.canonical_threshold,
        )
    db.link_search_logs_to_canonical(claim_id, canonical_id)
    db.update_claim_routing(claim_id, canonical_id=canonical_id)

    confidence_source = "delta_search" if cache_decision == "DELTA" else "fresh_search"
    verdict_id = db.insert_verdict(
        claim_id=claim_id, canonical_id=canonical_id, verdict_code=verdict_code,
        evidence_link=evidence_link, evidence_date=evidence_date,
        search_count=len(executed_queries), confidence_source=confidence_source,
        required_evidence_note=evidence_note, reasoning=reasoning,
    )
    emitter.emit("verdict.assembled", {
        "verdict_id": verdict_id, "claim_text": claim["claim_text"],
        "verdict_code": verdict_code, "evidence_link": evidence_link,
        "confidence_source": confidence_source, "cache_decision": cache_decision,
        "executed_queries": executed_queries, "degraded_reason": evidence_note,
    }, provider="app")
    return {"verdict_id": verdict_id, "verdict_code": verdict_code}


def assemble_unresolved_subject(*, claim: dict, claim_id: str, oai, db, settings,
                                emitter) -> dict:
    """판매/서비스 주체(브랜드)를 특정하지 못해 S4/S5를 건너뛰고 종료하는 경로
    (구축 요청 [A]). 브랜드 없이 만든 쿼리는 target_entity 매칭이 원리적으로
    불가능해 유효한 반례/뒷받침 근거가 될 수 없으므로, 검색을 강행하지 않고
    결정론적으로 UNVERIFIED를 부여한다."""
    note = "주장 대상 브랜드가 특정되지 않아 검증 불가"
    reasoning = _make_explanation(
        claim=claim, verdict_code="UNVERIFIED", winning=None,
        executed_queries=[], oai=oai, settings=settings, emitter=emitter,
        degraded_reason=note,
    )
    verdict_id = db.insert_verdict(
        claim_id=claim_id, canonical_id=None,
        verdict_code="UNVERIFIED",
        evidence_link=None, evidence_date=None, search_count=0,
        confidence_source="fresh_search", required_evidence_note=note,
        reasoning=reasoning,
    )
    emitter.emit("verdict.assembled", {
        "verdict_id": verdict_id, "claim_text": claim["claim_text"],
        "verdict_code": "UNVERIFIED",
        "degraded_reason": note,
    }, provider="app")
    return {"verdict_id": verdict_id, "verdict_code": "UNVERIFIED"}


def persist_puffery(*, claim: dict, claim_id: str, oai, db, settings, emitter) -> dict:
    """PUFFERY — 검색 tool_call 0건으로 종료하는 경로 (PRD N4).
    NOT_A_CLAIM은 판정 계약(4값) 대상이 아니므로 verdict row를 만들지 않는다."""
    reasoning = _make_explanation(claim=claim, verdict_code="PUFFERY", winning=None,
                                  executed_queries=[], oai=oai, settings=settings,
                                  emitter=emitter, degraded_reason=None)
    verdict_id = db.insert_verdict(
        claim_id=claim_id, canonical_id=None, verdict_code="PUFFERY",
        evidence_link=None, evidence_date=None, search_count=0,
        confidence_source="fresh_search", required_evidence_note=None,
        reasoning=reasoning,
    )
    emitter.emit("verdict.assembled", {
        "verdict_id": verdict_id, "claim_text": claim["claim_text"],
        "verdict_code": "PUFFERY", "search_tool_calls": 0,
    }, provider="app")
    return {"verdict_id": verdict_id, "verdict_code": "PUFFERY"}


def _make_explanation(*, claim, verdict_code, winning, executed_queries, oai, settings,
                      emitter, degraded_reason) -> str:
    """REPORTER(LLM) → 가드레일 1단(LLM) → 2단(정규식). 실패 시 결정론적 템플릿 폴백 —
    설명 생성이 죽어도 판정은 이미 확정돼 있고 파이프라인은 종료돼야 한다."""
    def _template() -> str:
        n = len(executed_queries)
        if verdict_code == "CONTRADICTED" and winning:
            return (f"기준(범주·지표·시점·시장)을 전부 충족하는 반박 근거 문서가 확인되었습니다: "
                    f"{winning['url']} (발행일: {winning['published_date'] or '미상'}). "
                    f"실행한 쿼리 {n}개는 화면에 표시됩니다.")
        if verdict_code == "CORROBORATED" and winning:
            return (f"기준(범주·지표·시점·시장)을 전부 충족하는 뒷받침 근거 문서가 확인되었습니다: "
                    f"{winning['url']} (발행일: {winning['published_date'] or '미상'}). "
                    f"이 근거 1건이 주장을 뒷받침한다는 사실만 전달하며, 그 이상으로 "
                    f"단정하지 않습니다. 실행한 쿼리 {n}개는 화면에 표시됩니다.")
        if verdict_code == "UNVERIFIED":
            base = (f"현재 탐색 범위(실행 쿼리 {n}개) 내에서 이 주장을 반증하거나 "
                    f"뒷받침하는 근거를 확인하지 못했습니다.")
            if degraded_reason:
                reason_text = degraded_reason.rstrip(". ")
                return f"{reason_text}. {base}"
            return base
        if verdict_code == "PUFFERY":
            return ("검증 가능한 사실 주장이 아니어서 검색을 실행하지 않았습니다. "
                    "주관적 표현은 참·거짓을 따질 대상이 아닙니다.")
        # 알 수 없는 verdict_code라도 긍정 결론을 내리지 않는 안전한 문구로 폴백
        return (f"현재 탐색 범위(실행 쿼리 {n}개) 내에서 이 주장을 반증하거나 "
                f"뒷받침하는 근거를 확인하지 못했습니다.")

    try:
        user = (
            f"클레임: {claim['claim_text']}\n"
            f"확정된 verdict: {verdict_code}\n"
            f"실행 쿼리 ({len(executed_queries)}개): {executed_queries}\n"
            + (f"반례 문서: {winning['url']} / 발행일 {winning['published_date']} / "
               f"인용: {winning['evidence_quote']}\n" if winning else "")
            + (f"참고 (부분 증거로 종료): {degraded_reason}\n" if degraded_reason else "")
        )
        report = oai.structured(
            model=settings.model_reporter, effort="medium",
            system=prompts.REPORTER, user=user,
            schema_name="reporter", schema=schemas.REPORTER_SCHEMA,
            emitter=emitter, stage="S6_REPORTER",
        )

        # ② 가드레일 1단: LLM으로 법적 결론 어휘 1차 차단
        try:
            flag = oai.structured(
                model=settings.model_guardrail, effort="none",
                system=prompts.COMMON_RULES
                + "\n다음 텍스트에 법적 결론 어휘(허위/거짓/위법/사기/불법/처벌 류)가 "
                  "포함되어 있는지만 판정합니다.",
                user=report.get("explanation", ""),
                schema_name="guardrail", schema=schemas.GUARDRAIL_SCHEMA,
                emitter=emitter, stage="S6_GUARDRAIL_LLM",
            )
            if flag.get("contains_banned_vocabulary"):
                report["explanation"] = _template()
        except Exception:
            pass  # 1단이 죽어도 2단(코드)이 있다

        # ③ 가드레일 2단: 정규식 — 걸리면 재생성 1회, 그래도 걸리면 정적 안전 문구
        def _regen(_payload: dict) -> dict:
            return {"explanation": _template(), "executed_queries": executed_queries}

        guarded = guard({"explanation": report.get("explanation", ""),
                         "executed_queries": executed_queries}, _regen)
        text = guarded["explanation"]
        # UNVERIFIED 전용 3단 가드레일: 반증도 근거도 없는 상태를 "진실일 가능성"
        # 같은 긍정 결론으로 포장하는 문구가 새면 안 되므로, LLM 지시만으로 두지
        # 않고 정규식으로도 강제 차단한다 — 걸리면 결정론적 템플릿으로 교체.
        if verdict_code == "UNVERIFIED" and contains_positive_conclusion({"e": text}):
            text = _template()
        return text if not contains_banned({"e": text}) else SAFE_FALLBACK
    except Exception:
        return _template()
