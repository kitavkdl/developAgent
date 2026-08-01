"""배포 부트스트랩 — Streamlit Community Cloud에는 shell이 없으므로,
앱 첫 부팅 시 마이그레이션과 카테고리 centroid 시드를 멱등 실행한다.

- 마이그레이션: 전부 IF NOT EXISTS / ON CONFLICT라 반복 실행 안전
- centroid: 비어 있는 카테고리만 계산 (OpenAI 키가 있을 때만; 없으면 건너뛰고
  분류는 폴백 카테고리로 동작 — 판정 로직에는 영향 없음, ARCHITECTURE §5)
"""
from __future__ import annotations

import glob
import os

# 카테고리별 대표 문장 (DB_SCHEMA.md §4 — 3~5개 임베딩 평균이 centroid)
CATEGORY_PHRASES: dict[str, list[str]] = {
    "BEAUTY_PERSONAL_CARE": ["수분 크림 미백 주름개선 화장품", "비건 세럼 피부 진정 앰플",
                             "선크림 자외선 차단 쿠션", "샴푸 탈모 완화 두피 케어"],
    "ELECTRONICS_APPLIANCE": ["무선 청소기 공기청정기 가전", "냉장고 세탁기 건조기 에너지효율",
                              "진공 블렌더 전기포트 주방가전", "노트북 스마트폰 이어폰"],
    "EDUCATION_EDTECH": ["온라인 강의 인터넷 강의 학원", "영어 회화 학습 앱 AI 튜터",
                         "코딩 부트캠프 자격증 교육"],
    "FOOD_SUPPLEMENT": ["유산균 프로바이오틱스 건강기능식품", "오메가3 루테인 비타민 영양제",
                        "콜라겐 다이어트 보조제", "김치 라면 즉석식품 간편식"],
    "FINANCE_FINTECH": ["주식 투자 앱 수수료 증권", "적금 대출 금리 은행",
                        "보험 비교 핀테크 서비스"],
    "FASHION_APPAREL": ["기능성 티셔츠 아우터 패션 브랜드", "운동화 스니커즈 데님",
                        "명품 가방 지갑 액세서리"],
    "PET": ["강아지 사료 고양이 간식 반려동물", "펫 보험 동물병원 용품",
            "고양이 모래 스크래처 장난감"],
    "KIDS_BABY": ["분유 기저귀 유아용품", "유모차 카시트 아기 장난감", "이유식 아기 세제"],
    "FITNESS_WELLNESS": ["헬스장 PT 홈트레이닝 피트니스", "요가 필라테스 스트레칭",
                         "단백질 보충제 운동 기구"],
    "HOUSEHOLD_CHEMICAL": ["세탁 세제 섬유유연제 생활화학", "주방 세제 살균 소독제",
                           "탈취제 방향제 곰팡이 제거제"],
    "DIGITAL_HEALTH": ["혈당 측정 앱 디지털 헬스케어", "수면 트래커 웨어러블 건강 관리",
                       "원격 진료 복약 관리 서비스"],
    "TRAVEL_LODGING": ["호텔 리조트 숙박 예약", "항공권 특가 여행 패키지",
                       "펜션 글램핑 국내 여행"],
    "REALESTATE_INTERIOR": ["아파트 분양 부동산 중개", "인테리어 시공 리모델링",
                            "소파 침대 매트리스 가구"],
}


def migration_files() -> list[str]:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return sorted(glob.glob(os.path.join(root, "db", "migrations", "*.sql")))


def run_bootstrap(db, oai, settings) -> dict:
    """반환: {"migrated": bool, "centroids_seeded": int} — 앱 시작 시 1회 호출."""
    db.migrate(migration_files())

    seeded = 0
    if settings.openai_api_key:
        with db.cursor() as cur:
            cur.execute(
                "SELECT category_id FROM industry_category WHERE centroid_embedding IS NULL"
            )
            rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            phrases = CATEGORY_PHRASES.get(row["category_id"])
            if not phrases:
                continue
            vecs = [oai.embed(p) for p in phrases]
            dim = len(vecs[0])
            centroid = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
            db.set_category_centroid(row["category_id"], centroid)
            seeded += 1
    return {"migrated": True, "centroids_seeded": seeded}
