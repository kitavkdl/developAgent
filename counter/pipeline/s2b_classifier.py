"""S2b. INDUSTRY CLASSIFIER — 임베딩 → 벡터 유사도 → 카테고리 배정.          [검색 0]

▸ 왜 병렬(S2a와): 판정 로직에 영향을 주지 않는다. 실패해도 검증은 정상 작동해야 한다.
▸ 왜 필요: canonical 매칭의 파티션 키. 파티셔닝의 목적은 스케일이 아니라 정확도 —
  서로 다른 업종의 "국내 최초"가 임베딩상 유사하다는 이유로 같은 canonical로 묶이면
  화장품 판정이 가전 클레임에 재사용되는 오매칭이 난다 (D-08).
▸ 왜 S3 앞: 카테고리가 확정돼야 캐시 매칭 파티션이 정해진다.

기존 카테고리 재사용을 우선한다 — 안 그러면 "화장품"/"뷰티"/"코스메틱"이 각각 생겨서
파티셔닝의 목적(캐시 히트 집중)이 무너진다 (ARCHITECTURE §5).
"""
from __future__ import annotations

import re

from .. import prompts, schemas


def resolve_industry_category(claim: dict, intake_result: dict, oai, db, settings,
                              emitter) -> tuple[dict, float | None, bool, list[float]]:
    """반환: (category_row{category_id,label,created_by}, similarity, is_new, claim_embedding)

    분류 실패 시 기본 카테고리로 폴백하고 파이프라인은 계속 진행 (ARCHITECTURE §7).
    """
    text = f"{intake_result.get('product_context') or ''} {claim['claim_text']}".strip()
    normalized = claim["normalized_text"]

    # 두 임베딩(canonical 매칭 키 / 카테고리 매칭용 맥락문)은 서로 독립이므로
    # 한 번의 요청으로 함께 받는다 — 순차 호출은 왕복만 두 배가 된다.
    try:
        if text and text != normalized:
            embedding, context_embedding = oai.embed_many([normalized, text])
        else:
            embedding = context_embedding = oai.embed(normalized)
    except Exception:
        # normalized 임베딩은 canonical 매칭 키라 없으면 진행 자체가 불가능하므로
        # 단건으로 한 번 더 시도하고(여기서도 실패하면 전파), 맥락문 임베딩만
        # 실패한 경우에는 기존과 같이 기본 카테고리로 폴백한다.
        embedding = oai.embed(normalized)
        return db.get_default_category(), None, False, embedding

    try:
        top = db.nearest_categories(context_embedding, k=5)
        if top and float(top[0]["similarity"]) >= settings.category_reuse_threshold:
            return top[0], float(top[0]["similarity"]), False, embedding

        # 임계 미달 → 신규 카테고리 생성 (Real-time Adaptability 시연 핵심 장면, D-07)
        label = oai.structured(
            model=settings.model_labeler, effort="low",
            system=prompts.CATEGORY_LABELER,
            user=f"클레임/제품 맥락: {text}",
            schema_name="category_label", schema=schemas.CATEGORY_LABEL_SCHEMA,
            emitter=emitter, stage="S2B_LABELER",
        )
        category_id = _slugify(label.get("code") or "NEW_CATEGORY")
        row = db.create_category(category_id, label.get("label_ko") or category_id,
                                context_embedding)
        return row, None, True, embedding
    except Exception:
        # 카테고리는 매칭 파티션 키일 뿐 판정 로직에 관여하지 않으므로,
        # 분류가 죽어도 검증은 계속 간다 (기본 카테고리 폴백)
        return db.get_default_category(), None, False, embedding


def _slugify(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s.strip()).strip("_").upper()
    return s[:50] or "NEW_CATEGORY"
