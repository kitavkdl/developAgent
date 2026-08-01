"""판정 결과 카드 — 메인 화면과 Raw Trace가 같은 형태로 결론을 보여주도록
한 곳에 모은다.

Raw Trace에서 "처리 과정"보다 "무엇을 결론냈고 그 근거가 무엇인지"를 먼저
보여주기 위해 app.py에 인라인으로 있던 렌더링을 이 모듈로 추출했다 —
두 화면이 각자 그리면 같은 job인데 화면마다 결론 표기가 달라진다.
"""
from __future__ import annotations

import json

import streamlit as st

from .ui_theme import DANGER, OK, cache_badge, plain_chip, verdict_badge

# falsifier 5차원 (gate.FALSIFIER_FIELDS)의 사람이 읽는 이름.
# 키는 applicability_check에 저장된 형태 그대로.
FIELD_LABELS = {
    "scope_match": "범주",
    "metric_match": "지표",
    "timeframe_match": "시점",
    "target_entity_match": "주체",
    "geography_match": "시장",
}


def render_verdict_cards(db, verdicts: list[dict]) -> None:
    """이미 조회된 verdict 목록을 카드로 렌더링한다.

    db는 카드마다 실행 쿼리 / 검토 문서를 추가 조회하는 데만 쓴다 (verdict
    자체는 호출부가 이미 갖고 있다 — 빈 목록 분기를 화면마다 다르게 쓰기 위함).
    """
    for v in verdicts:
        with st.container(border=True):
            _render_one(db, v)


def _render_one(db, v: dict) -> None:
    st.markdown(f"**{v['claim_text']}**")
    st.markdown(verdict_badge(v["verdict_code"]), unsafe_allow_html=True)

    if v.get("confidence_source") == "cached_reuse":
        st.markdown(
            cache_badge("HIT", v.get("search_count")) +
            " 재검색 없이 축적된 판정을 재사용했습니다.",
            unsafe_allow_html=True,
        )
    elif v.get("confidence_source") == "delta_search":
        st.markdown(
            cache_badge("DELTA") + " 축적된 증거 위에 시간 간극만 좁혀 재검색했습니다.",
            unsafe_allow_html=True,
        )

    if v.get("required_evidence_note"):
        st.markdown(f"부분 증거로 종료: {v['required_evidence_note']}")

    st.write(v.get("reasoning") or "")

    if v.get("evidence_link"):
        doc_label = "뒷받침 문서" if v["verdict_code"] == "CORROBORATED" else "반박 근거 문서"
        st.markdown(f"**{doc_label}**: [{v['evidence_link']}]({v['evidence_link']}) "
                    f"(발행일: {v.get('evidence_date') or '미상'})")

    queries = db.fetch_executed_queries(v["claim_id"], v.get("canonical_id"))
    # CONTRADICTED로 확정되지 않았어도 실제로 찾아서 검토한 문서를 노출 —
    # UNVERIFIED가 "조사 안 함"이 아니라 "찾아봤지만 기준 미충족"이라는
    # 걸 보여줘 오해를 줄인다.
    evidence_docs = db.fetch_evidence_reviewed(v["claim_id"], v.get("canonical_id"))

    if v["verdict_code"] != "PUFFERY":
        # 판정의 한계를 투명하게 — 이번 판정이 실제로 훑은 탐색 범위가
        # 어디까지였는지 숫자로 보여준다. 특히 UNVERIFIED에서 중요:
        # "안 찾아봤다"와 "이만큼 찾아봤는데도 없었다"는 전혀 다른 근거 강도다.
        domains = sorted({d["source_domain"] for d in evidence_docs
                          if d.get("source_domain")})
        scope = f"탐색 범위 — 실행 쿼리 {len(queries)}개 · 검토 문서 {len(evidence_docs)}건"
        if domains:
            scope += f" · 출처 도메인 {len(domains)}개"
        st.caption(scope)

    if queries:
        with st.expander(f"실행한 쿼리 전문 ({len(queries)}개)"):
            for q in queries:
                st.code(q, language=None)

    if evidence_docs:
        with st.expander(f"검토한 근거 문서 ({len(evidence_docs)}건)"):
            for doc in evidence_docs:
                _render_evidence_doc(doc)


def _render_evidence_doc(doc: dict) -> None:
    st.markdown(
        f"**[{doc.get('title') or doc['url']}]({doc['url']})** "
        f"(발행일: {doc.get('published_date') or '미상'}"
        f"{' · ' + doc['source_domain'] if doc.get('source_domain') else ''})"
    )
    if doc.get("snippet"):
        st.caption(doc["snippet"])

    check = doc.get("applicability_check")
    if isinstance(check, str):
        check = json.loads(check)
    if check:
        st.markdown(
            " ".join(
                plain_chip(label, OK if check.get(k) else DANGER)
                for k, label in FIELD_LABELS.items()
            ),
            unsafe_allow_html=True,
        )
        if check.get("supports_claim"):
            st.caption("뒷받침(CORROBORATED) 방향으로 평가된 문서")
        if check.get("is_syndicated_copy"):
            st.caption("동일 보도자료 재게재로 판단 — 독립 증거 아님")
        if check.get("insufficient_access"):
            st.caption("스니펫만으로 판단 불가 — 근거 부족 처리")

    if doc.get("reasoning"):
        st.caption(f"평가 근거: {doc['reasoning']}")
    st.divider()
