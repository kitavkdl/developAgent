"""업종 카테고리 centroid 임베딩 시드: python -m scripts.seed_categories

카테고리 임베딩과 claim 임베딩은 반드시 같은 모델(text-embedding-3-small)을 쓴다 —
섞으면 유사도가 무의미 (MODELS_AND_APIS §2.2).

각 카테고리의 대표 문구 여러 개를 임베딩한 뒤 평균(centroid)을 저장한다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from counter.clients.openai_client import OpenAIClient  # noqa: E402
from counter.db import Db  # noqa: E402
from counter.settings import load_settings  # noqa: E402

# 카테고리별 대표 문구 (centroid 계산용). 캐시 히트 시연을 위해 데모 데이터는
# 2~3개 업종에 몰아서 시드할 것 (D-08 실무 주의).
CATEGORY_PHRASES: dict[str, list[str]] = {
    "cosmetics_beauty": ["수분 크림 미백 주름개선 화장품", "비건 세럼 피부 진정 앰플", "선크림 자외선 차단 쿠션 팩트"],
    "food_beverage": ["김치 라면 즉석식품 간편식", "콜드브루 커피 원두 음료", "유기농 과일 주스 스낵"],
    "home_appliance": ["무선 청소기 공기청정기 가전", "냉장고 세탁기 건조기 에너지효율", "진공 블렌더 전기포트 주방가전"],
    "health_supplement": ["유산균 프로바이오틱스 건강기능식품", "오메가3 루테인 비타민 영양제", "콜라겐 다이어트 보조제"],
    "fashion": ["기능성 티셔츠 아우터 패션 브랜드", "운동화 스니커즈 데님", "명품 가방 지갑 액세서리"],
    "mobile_app_service": ["모바일 앱 구독 서비스 플랫폼", "배달 앱 중고거래 서비스", "AI 챗봇 사진 편집 앱"],
    "finance": ["주식 투자 앱 수수료 증권", "적금 대출 금리 은행", "보험 비교 핀테크 서비스"],
    "education": ["온라인 강의 인터넷 강의 학원", "영어 회화 학습 앱", "코딩 부트캠프 자격증 교육"],
    "travel_lodging": ["호텔 리조트 숙박 예약", "항공권 특가 여행 패키지", "펜션 글램핑 국내 여행"],
    "automotive": ["전기차 주행거리 자동차", "타이어 엔진오일 차량 용품", "중고차 신차 SUV 세단"],
    "furniture_interior": ["소파 침대 매트리스 가구", "붙박이장 인테리어 시공", "조명 커튼 홈데코"],
    "medical_device": ["체온계 혈압계 의료기기", "저주파 마사지기 치료기", "콘택트렌즈 보청기"],
    "baby_kids": ["분유 기저귀 유아용품", "유모차 카시트 아기 장난감", "이유식 아기 세제"],
}


def main() -> None:
    settings = load_settings()
    db = Db(settings)
    oai = OpenAIClient(settings)
    with db.cursor() as cur:
        cur.execute("SELECT id, code FROM industry_category WHERE centroid_embedding IS NULL")
        rows = cur.fetchall()
    for row in rows:
        phrases = CATEGORY_PHRASES.get(row["code"])
        if not phrases:
            print(f"skip (문구 없음): {row['code']}")
            continue
        vecs = [oai.embed(p) for p in phrases]
        dim = len(vecs[0])
        centroid = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
        db.set_category_centroid(row["id"], centroid)
        print(f"centroid 저장: {row['code']}")
    print("완료")


if __name__ == "__main__":
    main()
