export interface IndustryCategorySeed {
  categoryId: string;
  label: string;
  createdBy: "seed";
  centroidPhrases: string[];
}

export const CATEGORY_REUSE_THRESHOLD_REFERENCE = 0.75;

export const INDUSTRY_CATEGORY_SEEDS: IndustryCategorySeed[] = [
  {
    categoryId: "BEAUTY_PERSONAL_CARE",
    label: "뷰티/퍼스널케어",
    createdBy: "seed",
    centroidPhrases: [
      "수분 크림 미백 주름개선 화장품",
      "비건 세럼 피부 진정 앰플",
      "선크림 자외선 차단 쿠션",
      "샴푸 탈모 완화 두피 케어",
    ],
  },
  {
    categoryId: "ELECTRONICS_APPLIANCE",
    label: "가전/전자",
    createdBy: "seed",
    centroidPhrases: [
      "무선 청소기 공기청정기 가전",
      "냉장고 세탁기 건조기 에너지효율",
      "진공 블렌더 전기포트 주방가전",
      "노트북 스마트폰 이어폰",
    ],
  },
  {
    categoryId: "EDUCATION_EDTECH",
    label: "교육/에듀테크",
    createdBy: "seed",
    centroidPhrases: [
      "온라인 강의 인터넷 강의 학원",
      "영어 회화 학습 앱 AI 튜터",
      "코딩 부트캠프 자격증 교육",
    ],
  },
  {
    categoryId: "FOOD_SUPPLEMENT",
    label: "식품/건강기능식품",
    createdBy: "seed",
    centroidPhrases: [
      "유산균 프로바이오틱스 건강기능식품",
      "오메가3 루테인 비타민 영양제",
      "콜라겐 다이어트 보조제",
      "김치 라면 즉석식품 간편식",
    ],
  },
  {
    categoryId: "FINANCE_FINTECH",
    label: "금융/핀테크",
    createdBy: "seed",
    centroidPhrases: [
      "주식 투자 앱 수수료 증권",
      "적금 대출 금리 은행",
      "보험 비교 핀테크 서비스",
    ],
  },
  {
    categoryId: "FASHION_APPAREL",
    label: "패션/의류",
    createdBy: "seed",
    centroidPhrases: [
      "기능성 티셔츠 아우터 패션 브랜드",
      "운동화 스니커즈 데님",
      "명품 가방 지갑 액세서리",
    ],
  },
  {
    categoryId: "PET",
    label: "반려동물",
    createdBy: "seed",
    centroidPhrases: [
      "강아지 사료 고양이 간식 반려동물",
      "펫 보험 동물병원 용품",
      "고양이 모래 스크래처 장난감",
    ],
  },
  {
    categoryId: "KIDS_BABY",
    label: "유아동",
    createdBy: "seed",
    centroidPhrases: [
      "분유 기저귀 유아용품",
      "유모차 카시트 아기 장난감",
      "이유식 아기 세제",
    ],
  },
  {
    categoryId: "FITNESS_WELLNESS",
    label: "피트니스/웰니스",
    createdBy: "seed",
    centroidPhrases: [
      "헬스장 PT 홈트레이닝 피트니스",
      "요가 필라테스 스트레칭",
      "단백질 보충제 운동 기구",
    ],
  },
  {
    categoryId: "HOUSEHOLD_CHEMICAL",
    label: "생활화학",
    createdBy: "seed",
    centroidPhrases: [
      "세탁 세제 섬유유연제 생활화학",
      "주방 세제 살균 소독제",
      "탈취제 방향제 곰팡이 제거제",
    ],
  },
  {
    categoryId: "DIGITAL_HEALTH",
    label: "디지털헬스",
    createdBy: "seed",
    centroidPhrases: [
      "혈당 측정 앱 디지털 헬스케어",
      "수면 트래커 웨어러블 건강 관리",
      "원격 진료 복약 관리 서비스",
    ],
  },
  {
    categoryId: "TRAVEL_LODGING",
    label: "여행/숙박",
    createdBy: "seed",
    centroidPhrases: [
      "호텔 리조트 숙박 예약",
      "항공권 특가 여행 패키지",
      "펜션 글램핑 국내 여행",
    ],
  },
  {
    categoryId: "REALESTATE_INTERIOR",
    label: "부동산/인테리어",
    createdBy: "seed",
    centroidPhrases: [
      "아파트 분양 부동산 중개",
      "인테리어 시공 리모델링",
      "소파 침대 매트리스 가구",
    ],
  },
  {
    categoryId: "UNCATEGORIZED",
    label: "미분류 (폴백)",
    createdBy: "seed",
    centroidPhrases: [],
  },
];

export function phraseKeywords(phrase: string): string[] {
  return Array.from(
    new Set(
      phrase
        .split(/\s+/)
        .map((keyword) => keyword.trim())
        .filter(Boolean),
    ),
  );
}
